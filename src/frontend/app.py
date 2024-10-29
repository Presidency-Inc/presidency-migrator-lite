from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
import os
import sys
import json

# Add the parent directory to Python path to import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.testrail_client import TestRailClient

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_random_secret_key'  # Replace with a secure random key

def get_testrail_client():
    config = session.get('testrail_config')
    if not config:
        return None
    return TestRailClient(
        base_url=config['url'],
        username=config['username'],
        api_key=config['apiKey']
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['POST'])
def save_config():
    try:
        config = request.get_json()
        if not config:
            return jsonify({'error': 'Invalid configuration'}), 400
        
        # Save configuration in session
        session['testrail_config'] = config
        
        # Return the saved config for verification
        return jsonify({
            'message': 'Configuration saved',
            'saved_config': session.get('testrail_config')
        })
    except Exception as e:
        app.logger.error(f"Error saving configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    try:
        # Initialize TestRail client
        app.logger.debug("Session contents: %s", dict(session))
        testrail_client = get_testrail_client()
        if not testrail_client:
            app.logger.error("TestRail client initialization failed")
            return jsonify({'error': 'TestRail client not initialized'}), 400

        # Get projects
        projects = testrail_client.get_projects()
        app.logger.debug(f"Projects fetched: {projects}")
        return jsonify(projects)
    except Exception as e:
        app.logger.error(f"Error fetching projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/project/<int:project_id>', methods=['GET'])
def get_project_details(project_id):
    try:
        testrail_client = get_testrail_client()
        if not testrail_client:
            return jsonify({'error': 'TestRail client not initialized'}), 400

        # Get project details
        project = testrail_client.get_project(project_id)
        
        # Get suites
        suites = testrail_client.get_suites(project_id)
        
        # Get sections - now returns just the array of sections
        sections = testrail_client.get_sections(project_id)
        
        # Get test cases
        test_cases = testrail_client.get_all_test_cases(project_id)

        return jsonify({
            'project': project,
            'suites': suites,
            'sections': sections,  # This will now be the array of sections
            'test_cases': test_cases
        })
    except Exception as e:
        app.logger.error(f"Error fetching project details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/migrate', methods=['POST'])
def start_migration():
    try:
        testrail_client = get_testrail_client()
        if not testrail_client:
            return jsonify({'error': 'TestRail client not initialized'}), 400

        data = request.json
        project_id = data.get('projectId')
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400

        project = testrail_client.get_project(project_id)

        # Start migration process (implement your migration logic here)
        # For now, just return a success message
        return jsonify({
            'message': 'Migration started',
            'projectName': project['name']
        })
    except Exception as e:
        app.logger.error(f"Error starting migration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    return jsonify({
        'has_config': 'testrail_config' in session,
        'config': session.get('testrail_config')
    })

if __name__ == '__main__':
    app.run(debug=True, port=3000)