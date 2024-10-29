document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const configForm = document.getElementById('configForm');
    const configCard = document.getElementById('configCard');
    const projectCard = document.getElementById('projectCard');
    const projectSelect = document.getElementById('projectSelect');
    const startMigrationBtn = document.getElementById('startMigration');
    const statusDiv = document.getElementById('status');
    const statusMessage = document.getElementById('statusMessage');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const toggleApiKeyBtn = document.getElementById('toggleApiKey');
    const apiKeyInput = document.getElementById('testrailApiKey');
  
    // Toggle API Key visibility
    toggleApiKeyBtn.addEventListener('click', () => {
      const type = apiKeyInput.type === 'password' ? 'text' : 'password';
      apiKeyInput.type = type;
      toggleApiKeyBtn.innerHTML = `<i class="fas fa-eye${type === 'password' ? '' : '-slash'}"></i>`;
    });
  
    // Handle configuration form submission
    configForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Check form validity
      if (!configForm.checkValidity()) {
        // If invalid, display validation messages
        configForm.reportValidity();
        return;
      }

      // Proceed with submission if form is valid
      let url = document.getElementById('testrailUrl').value.trim();
      // Ensure URL doesn't end with a slash
      url = url.replace(/\/+$/, '');
      
      const config = {
        url,
        username: document.getElementById('testrailUser').value.trim(),
        apiKey: document.getElementById('testrailApiKey').value.trim()
      };
  
      try {
        showLoading(true, configForm.querySelector('.btn-primary'));
        
        // Save configuration
        const saveResponse = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
          credentials: 'include'  // Important! Include credentials
        });
        
        if (!saveResponse.ok) throw new Error('Failed to save configuration');
        
        // Test configuration by loading projects
        await loadProjects();
        
        // Show success message
        showSuccess('Connected to TestRail successfully');
        
        // Show project selection
        configCard.classList.add('hidden');
        projectCard.classList.remove('hidden');
      } catch (error) {
        console.error('Error:', error);
        showError('Failed to connect to TestRail. Please check your configuration.');
      } finally {
        showLoading(false, configForm.querySelector('.btn-primary'));
      }
    });
  
    async function loadProjects() {
      try {
        showLoading(true, startMigrationBtn);
  
        const response = await fetch('/api/projects', {
          credentials: 'include'  // Add this line
        });
        
        if (!response.ok) throw new Error('Failed to load projects');
        
        const projects = await response.json();
        console.log('Projects loaded:', projects); // Add this for debugging
        
        projectSelect.innerHTML = '<option value="">Select a project...</option>';
        projects.forEach(project => {
          const option = document.createElement('option');
          option.value = project.id;
          option.textContent = `${project.name} (${project.is_completed ? 'Completed' : 'Active'})`;
          projectSelect.appendChild(option);
        });
      } catch (error) {
        console.error('Error loading projects:', error);
        showError('Error loading projects. Please check your TestRail configuration.');
      } finally {
        showLoading(false, startMigrationBtn);
      }
    }
  
    async function loadProjectDetails(projectId) {
      try {
        const response = await fetch(`/api/project/${projectId}`);
        if (!response.ok) throw new Error('Failed to load project details');
        
        const data = await response.json();
        return data;
      } catch (error) {
        showError('Error loading project details');
      }
    }
  
    function showLoading(isLoading, button) {
      const btnContent = button.querySelector('.btn-content');
      const loadingSpinner = button.querySelector('.loading');
      btnContent.classList.toggle('hidden', isLoading);
      loadingSpinner.classList.toggle('hidden', !isLoading);
      button.disabled = isLoading;
    }
  
    function showError(message) {
      statusDiv.classList.remove('hidden');
      statusMessage.innerHTML = `
        <div class="status-icon error">
          <i class="fas fa-times"></i>
        </div>
        ${message}
      `;
      statusMessage.className = 'status-message error';
      progressContainer.classList.add('hidden');
    }
  
    function showSuccess(message) {
      statusDiv.classList.remove('hidden');
      statusMessage.innerHTML = `
        <div class="status-icon success">
          <i class="fas fa-check"></i>
        </div>
        ${message}
      `;
      statusMessage.className = 'status-message success';
    }
  
    function updateProgress(progress) {
      progressBar.style.width = `${progress}%`;
    }
  
    projectSelect.addEventListener('change', async () => {
      const projectId = projectSelect.value;
      if (!projectId) return;
  
      try {
        const details = await loadProjectDetails(projectId);
        let suiteInfo = '';
        
        switch (details.project.suite_mode) {
          case 1:
            suiteInfo = 'Single Suite Mode';
            break;
          case 2:
            suiteInfo = 'Single Suite + Baselines Mode';
            break;
          case 3:
            suiteInfo = `Multiple Suites Mode (${details.suites.length} suites)`;
            break;
          default:
            suiteInfo = 'Unknown Suite Mode';
            break;
        }
  
        // Now sections will be an array, so we can get its length directly
        const sectionsCount = details.sections ? details.sections.length : 0;
  
        showSuccess(`
          Project: ${details.project.name}<br>
          Suite Mode: ${suiteInfo}<br>
          Sections: ${sectionsCount}<br>
          Announcement: ${details.project.announcement || 'None'}
        `);
      } catch (error) {
        showError('Failed to load project details');
      }
    });
  
    startMigrationBtn.addEventListener('click', async () => {
      const projectId = projectSelect.value;
      if (!projectId) {
        showError('Please select a project first');
        return;
      }
  
      try {
        showLoading(true, startMigrationBtn);
        const response = await fetch('/api/migrate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectId }),
        });
  
        if (!response.ok) throw new Error('Migration failed');
        
        const result = await response.json();
        showSuccess(`Migration started for project: ${result.projectName}`);
        progressContainer.classList.remove('hidden');
        
        // Simulate progress for demo purposes
        let progress = 0;
        const interval = setInterval(() => {
          progress += 1;
          updateProgress(progress);
          if (progress >= 100) {
            clearInterval(interval);
            showSuccess(`Successfully started migration for ${result.projectName}`);
          }
        }, 100);
      } catch (error) {
        showError('Migration failed. Please try again.');
      } finally {
        showLoading(false, startMigrationBtn);
      }
    });

    // Add this function for debugging
    async function checkSession() {
      try {
        const response = await fetch('/api/debug/session', {
          credentials: 'include'
        });
        const data = await response.json();
        console.log('Session data:', data);
      } catch (error) {
        console.error('Error checking session:', error);
      }
    }
  });