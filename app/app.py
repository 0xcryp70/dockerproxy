# app/app.py

from flask import Flask, request, render_template, jsonify
from celery import Celery
import docker
import re
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'  # Redis broker URL
app.config['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

def validate_image_name(image_name):
    # Regex pattern to validate Docker image names
    pattern = r'^[\w][\w.-]{0,127}(?:/[\w][\w.-]{0,127})*(?::[\w][\w.-]{0,127})?$'
    return re.match(pattern, image_name) is not None

@celery.task(bind=True)
def process_image_task(self, image_name):
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'step': 'Validating image name'})

        # Validate image name
        if not validate_image_name(image_name):
            return {'status': 'error', 'message': 'Invalid image name.'}

        # Update task state
        self.update_state(state='PROGRESS', meta={'step': 'Pulling image'})

        # Pull the image from Docker Hub
        image = client.images.pull(image_name)

        # Use external registry address for tagging and pushing
        registry_address = os.environ.get('REGISTRY_ADDRESS', 'registry.xcr9.site')
        new_image_name = f'{registry_address}/{image_name}'

        # Tag the image
        self.update_state(state='PROGRESS', meta={'step': 'Tagging image'})
        image.tag(new_image_name)

        # Push the image to the registry
        self.update_state(state='PROGRESS', meta={'step': 'Pushing image'})
        push_log = client.images.push(new_image_name)
        logging.info(f'Push output: {push_log}')

        return {'status': 'success', 'new_image_name': new_image_name}

    except docker.errors.APIError as e:
        error_message = f'Docker API error: {str(e)}'
        logging.error(error_message)
        return {'status': 'error', 'message': error_message}

    except Exception as e:
        error_message = f'Unexpected error: {str(e)}'
        logging.error(error_message)
        return {'status': 'error', 'message': error_message}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        image_name = request.form.get('image_name')
        # Start the background task
        task = process_image_task.apply_async(args=[image_name])
        return render_template('progress.html', task_id=task.id)
    return render_template('index.html')

@app.route('/status/<task_id>')
def task_status(task_id):
    task = process_image_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # Task has not started yet
        response = {'state': task.state, 'progress': 0}
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'progress': 50,
            'step': task.info.get('step', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'progress': 100,
            'result': task.info
        }
    else:
        # Something went wrong in the background job
        response = {
            'state': task.state,
            'progress': 100,
            'result': str(task.info)
        }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

