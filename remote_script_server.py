from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/run-script', methods=['POST'])
def run_script():
    try:
        # Change 'your_script.py' to the path of your Python script
        result = subprocess.run(['python3', 'test.py'], capture_output=True, text=True)
        return {
            'status': 'success',
            'output': result.stdout,
            'error': result.stderr
        }
    except Exception as e:
        return {'status': 'failure', 'error': str(e)}

if __name__ == '__main__':
    # Listen on all network interfaces
    app.run(host='0.0.0.0', port=5000)
