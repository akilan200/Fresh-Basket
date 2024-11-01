from functools import wraps
from flask import request, jsonify
import boto3

def require_iam_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.headers.get('X-AWS-Auth')
        if not auth_token:
            return jsonify({'error': 'No authentication token'}), 401
        
        try:
            iam = boto3.client('iam')
            response = iam.verify_session_token(Token=auth_token)
            if response['Valid']:
                return f(*args, **kwargs)
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    
    return decorated_function

def encrypt_health_data(data):
    try:
        kms = boto3.client('kms')
        response = kms.encrypt(
            KeyId='your-kms-key-id',
            Plaintext=str(data).encode()
        )
        return response['CiphertextBlob']
    except Exception as e:
        return None
