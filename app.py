import os
import re
import requests
import uuid
from flask import Flask, render_template, request, jsonify, send_file, session, redirect
from openai import OpenAI
from io import BytesIO
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

app.config['SESSION_PERMANENT'] = False

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'dummy-openai-key')
STABILITY_API_KEY = os.environ.get('STABILITY_API_KEY', 'dummy-stability-key')
REMOVEBG_API_KEY = os.environ.get('REMOVEBG_API_KEY', 'dummy-removebg-key')
MESHY_API_KEY = os.environ.get('MESHY_API_KEY', 'dummy-meshy-key')

client = OpenAI(api_key=OPENAI_API_KEY)


def is_english(text):
    """Check if text contains only English characters"""
    return bool(re.match(r'^[a-zA-Z0-9\s\.,!?\-]+$', text))


def translate_to_english(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f'Translate to English: "{text}"'}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def enhance_prompt(prompt):
    return f"{prompt}, isometric view, centered, no shadow, without background, plain white background"


def generate_dalle_image(prompt):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"DALL-E error: {e}")
        return None


def generate_stability_image(prompt):
    try:
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Content-Type": "application/json",
        }
        
        body = {
            "text_prompts": [
                {
                    "text": prompt
                }
            ],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        }
        
        response = requests.post(url, headers=headers, json=body)
        
        if response.ok:
            data = response.json()
            return f"data:image/png;base64,{data['artifacts'][0]['base64']}"
        else:
            print(f"Stability AI error: {response.text}")
            return None
    except Exception as e:
        print(f"Stability AI error: {e}")
        return None


def remove_background(image_url):
    try:
        headers = {'X-Api-Key': REMOVEBG_API_KEY}
        data = {'size': 'auto'}
        
        if image_url.startswith('data:image'):
            header, base64_data = image_url.split(',', 1)
            image_bytes = base64.b64decode(base64_data)
            
            if 'image/jpeg' in header or 'image/jpg' in header:
                filename = 'image.jpg'
            else:
                filename = 'image.png'
            
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': (filename, image_bytes)},
                data=data,
                headers=headers,
            )
        else:
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_url': (None, image_url)},
                data=data,
                headers=headers,
            )
        
        if response.status_code == requests.codes.ok:
            img_base64 = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
        else:
            print(f"remove.bg error: {response.status_code}, {response.text}")
            return image_url
    except Exception as e:
        print(f"Background removal error: {e}")
        return image_url


def generate_3d_model(image_url):
    try:
        headers = {
            "Authorization": f"Bearer {MESHY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        submit_url = "https://api.meshy.ai/openapi/v1/image-to-3d"
        
        payload = {
            "image_url": image_url,
            "ai_model": "meshy-5",
            "topology": "triangle",
            "should_remesh": True,
            "should_texture": True,
            "enable_pbr": True,
        }
        
        response = requests.post(submit_url, headers=headers, json=payload)
        
        if response.ok:
            data = response.json()
            task_id = data.get('result')
            print(f"3D model generation started: {task_id}")
            return task_id
        else:
            print(f"Meshy.ai error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"3D generation error: {e}")
        return None


def get_3d_model_status(task_id):
    try:
        headers = {
            "Authorization": f"Bearer {MESHY_API_KEY}",
        }
        
        status_url = f"https://api.meshy.ai/openapi/v1/image-to-3d/{task_id}"
        response = requests.get(status_url, headers=headers)
        
        if response.ok:
            data = response.json()
            print(f"Task {task_id} status: {data.get('status')} - Progress: {data.get('progress', 0)}%")
            return data
        else:
            print(f"Status check error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Status check error: {e}")
        return None


def refine_3d_model(preview_task_id):
    print("Warning: refine mode not found in official API docs.")
    print("Use generate_3d_model with topology='quad' and higher polycount instead.")
    return None


def remesh_model(input_task_id=None, model_url=None, target_polycount=30000, 
                 topology="triangle", target_formats=None):
    try:
        if not input_task_id and not model_url:
            print("Error: Must provide either input_task_id or model_url")
            return None
            
        headers = {
            "Authorization": f"Bearer {MESHY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        remesh_url = "https://api.meshy.ai/openapi/v1/remesh"
        
        payload = {
            "topology": topology,
            "target_polycount": target_polycount,
        }
        
        if input_task_id:
            payload["input_task_id"] = input_task_id
        else:
            payload["model_url"] = model_url
            
        if target_formats:
            payload["target_formats"] = target_formats
        else:
            payload["target_formats"] = ["glb"]
        
        response = requests.post(remesh_url, headers=headers, json=payload)
        
        if response.ok:
            data = response.json()
            task_id = data.get('result')
            print(f"Remesh task started: {task_id}")
            return task_id
        else:
            print(f"Remesh error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Remesh error: {e}")
        return None


def get_remesh_status(task_id):
    try:
        headers = {
            "Authorization": f"Bearer {MESHY_API_KEY}",
        }
        
        status_url = f"https://api.meshy.ai/openapi/v1/remesh/{task_id}"
        response = requests.get(status_url, headers=headers)
        
        if response.ok:
            data = response.json()
            print(f"Remesh task {task_id} status: {data.get('status')} - Progress: {data.get('progress', 0)}%")
            return data
        else:
            print(f"Remesh status check error: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Remesh status check error: {e}")
        return None


def convert_obj_to_stl(obj_url):
    try:
        # For simplicity, we can use the GLB format which is widely supported
        # Or download OBJ and convert to STL using a library
        # For now, just return the model URL - actual conversion would require
        # additional libraries like trimesh or pymesh
        
        if obj_url.endswith('.obj'):
            # Could implement local conversion here with trimesh
            # import trimesh
            # mesh = trimesh.load(obj_url)
            # mesh.export('output.stl')
            pass
        
        return obj_url
    except Exception as e:
        print(f"Conversion error: {e}")
        return None


@app.route('/')
def index():
    """Main page for prompt input"""
    return render_template('index.html')


@app.route('/generate-images', methods=['POST'])
def generate_images():
    """Generate two images from prompt"""
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    # Translate if not English
    if not is_english(prompt):
        prompt = translate_to_english(prompt)
    
    # Enhance prompt
    enhanced_prompt = enhance_prompt(prompt)
    
    # Generate images
    dalle_image = generate_dalle_image(enhanced_prompt)
    stability_image = generate_stability_image(enhanced_prompt)
    
    if not dalle_image or not stability_image:
        return jsonify({'error': 'Failed to generate images'}), 500
    
    # Remove backgrounds (now handles both URLs and data URIs)
    dalle_image_nobg = remove_background(dalle_image)
    stability_image_nobg = remove_background(stability_image)
    
    # Generate unique session ID for this generation
    session_id = str(uuid.uuid4())
    
    # Create temp directory for storing images if it doesn't exist
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_images')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Save images to temporary files instead of session
    image1_filename = f"{session_id}_image1.txt"
    image2_filename = f"{session_id}_image2.txt"
    
    with open(os.path.join(temp_dir, image1_filename), 'w') as f:
        f.write(dalle_image_nobg)
    with open(os.path.join(temp_dir, image2_filename), 'w') as f:
        f.write(stability_image_nobg)
    
    # Store only the session ID and prompt in session (small data)
    session['session_id'] = session_id
    session['prompt'] = prompt
    
    return jsonify({
        'image1': dalle_image_nobg,
        'image2': stability_image_nobg,
        'prompt': prompt
    })


@app.route('/selection')
def selection():
    """Page for selecting which image to use"""
    session_id = session.get('session_id')
    
    if not session_id:
        return redirect('/')
    
    # Read images from temporary files
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_images')
    image1_path = os.path.join(temp_dir, f"{session_id}_image1.txt")
    image2_path = os.path.join(temp_dir, f"{session_id}_image2.txt")
    
    try:
        with open(image1_path, 'r') as f:
            image1 = f.read()
        with open(image2_path, 'r') as f:
            image2 = f.read()
    except FileNotFoundError:
        return redirect('/')
    
    return render_template('selection.html', image1=image1, image2=image2)


@app.route('/select-image', methods=['POST'])
def select_image():
    """Process selected image"""
    data = request.json
    selected = data.get('selected')  # 'image1' or 'image2'
    session_id = session.get('session_id')
    
    if selected not in ['image1', 'image2']:
        return jsonify({'error': 'Invalid selection'}), 400
    
    if not session_id:
        return jsonify({'error': 'Session expired'}), 404
    
    # Read selected image from file
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_images')
    filename = f"{session_id}_{selected}.txt"
    filepath = os.path.join(temp_dir, filename)
    
    try:
        with open(filepath, 'r') as f:
            selected_image = f.read()
    except FileNotFoundError:
        return jsonify({'error': 'Image not found'}), 404
    
    # Generate 3D model
    task_id = generate_3d_model(selected_image)
    
    if not task_id:
        return jsonify({'error': 'Failed to generate 3D model'}), 500
    
    # Store only task_id in session (small data)
    session['task_id'] = task_id
    
    # Save selected image to a specific file for this task
    selected_image_file = f"{session_id}_selected.txt"
    with open(os.path.join(temp_dir, selected_image_file), 'w') as f:
        f.write(selected_image)
    
    return jsonify({'task_id': task_id})


@app.route('/viewer')
def viewer():
    """3D model viewer page"""
    task_id = session.get('task_id')
    
    if not task_id:
        return redirect('/')
    
    return render_template('viewer.html', task_id=task_id)


@app.route('/model-status/<task_id>')
def model_status(task_id):
    """Check 3D model generation status"""
    status = get_3d_model_status(task_id)
    
    if not status:
        return jsonify({'error': 'Failed to get status'}), 500
    
    # Replace direct model URLs with proxied URLs to avoid CORS issues
    if status.get('status') == 'SUCCEEDED' and status.get('model_urls'):
        # Provide proxied URL instead of direct Meshy URL
        status['model_url_proxy'] = f"/proxy-model/{task_id}/model.glb"
    
    return jsonify(status)


@app.route('/remesh-model', methods=['POST'])
def remesh_model_endpoint():
    """Optimize a 3D model by reducing polygon count"""
    data = request.json
    model_url = data.get('model_url')
    
    if not model_url:
        return jsonify({'error': 'No model URL provided'}), 400
    
    task_id = remesh_model(model_url)
    
    if not task_id:
        return jsonify({'error': 'Failed to start remesh'}), 500
    
    return jsonify({'task_id': task_id})


@app.route('/remesh-status/<task_id>')
def remesh_status_endpoint(task_id):
    """Check remesh task status"""
    status = get_remesh_status(task_id)
    
    if not status:
        return jsonify({'error': 'Failed to get remesh status'}), 500
    
    return jsonify(status)


@app.route('/download-model/<task_id>')
def download_model(task_id):
    """Download 3D model in the requested format"""
    format_type = request.args.get('format', 'glb').lower()
    
    # Get model info
    status = get_3d_model_status(task_id)
    
    if not status or status.get('status') != 'SUCCEEDED':
        return jsonify({'error': 'Model not ready', 'status': status.get('status') if status else 'unknown'}), 400
    
    # Get the appropriate model URL based on format
    model_urls = status.get('model_urls', {})
    
    format_map = {
        'glb': model_urls.get('glb'),
        'fbx': model_urls.get('fbx'),
        'obj': model_urls.get('obj'),
        'usdz': model_urls.get('usdz'),
        'mtl': model_urls.get('mtl')
    }
    
    model_url = format_map.get(format_type)
    
    if not model_url:
        return jsonify({'error': f'Format {format_type} not available', 'available_formats': list(model_urls.keys())}), 400
    
    # Download and serve the file
    try:
        response = requests.get(model_url)
        if response.ok:
            mime_types = {
                'glb': 'model/gltf-binary',
                'fbx': 'application/octet-stream',
                'obj': 'text/plain',
                'usdz': 'model/vnd.usdz+zip',
                'mtl': 'text/plain'
            }
            
            return send_file(
                BytesIO(response.content),
                mimetype=mime_types.get(format_type, 'application/octet-stream'),
                as_attachment=True,
                download_name=f'model_{task_id}.{format_type}'
            )
        else:
            return jsonify({'error': 'Failed to download model'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy-model/<task_id>/<filename>')
def proxy_model(task_id, filename):
    """Proxy 3D model files to avoid CORS issues
    
    Fetches the model file from Meshy's servers and serves it through our backend.
    This avoids CORS errors when loading models in the browser.
    """
    # Get model info
    status = get_3d_model_status(task_id)
    
    if not status or status.get('status') != 'SUCCEEDED':
        return jsonify({'error': 'Model not ready'}), 400
    
    # Get GLB model URL
    model_urls = status.get('model_urls', {})
    glb_url = model_urls.get('glb')
    
    if not glb_url:
        return jsonify({'error': 'GLB model not available'}), 400
    
    # Fetch and proxy the model file
    try:
        response = requests.get(glb_url)
        if response.ok:
            return send_file(
                BytesIO(response.content),
                mimetype='model/gltf-binary',
                as_attachment=False,  # Not a download, just serving
                download_name=filename
            )
        else:
            return jsonify({'error': 'Failed to fetch model'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/convert-to-stl', methods=['POST'])
def convert_to_stl():
    data = request.json
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'error': 'No task ID provided'}), 400
    
    remesh_task_id = remesh_model(
        input_task_id=task_id,
        topology="triangle",
        target_formats=["stl"]
    )
    
    if not remesh_task_id:
        return jsonify({'error': 'Failed to start STL conversion'}), 500
    
    return jsonify({'remesh_task_id': remesh_task_id})


@app.route('/download-stl/<task_id>')
def download_stl(task_id):
    status = get_remesh_status(task_id)
    
    if not status or status.get('status') != 'SUCCEEDED':
        return jsonify({'error': 'STL file not ready', 'status': status.get('status') if status else 'unknown'}), 400
    
    model_urls = status.get('model_urls', {})
    stl_url = model_urls.get('stl')
    
    if not stl_url:
        return jsonify({'error': 'STL format not available', 'available_formats': list(model_urls.keys())}), 400
    
    try:
        response = requests.get(stl_url)
        if response.ok:
            return send_file(
                BytesIO(response.content),
                mimetype='application/sla',
                as_attachment=True,
                download_name=f'model_{task_id}.stl'
            )
        else:
            return jsonify({'error': 'Failed to download STL file'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
