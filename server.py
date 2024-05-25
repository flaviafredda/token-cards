from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from rsa_accumulator import random_coprime_with_totient, n_for_RSA, rsa_accumulate, root_extraction

from ipfs import *

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///generated_values.db'
db = SQLAlchemy(app)

def setup_app(application): 
    with application.app_context():
        db.create_all()
    # Create and open the file for writing (if it already exists by default it overwrites it)
    with open('accumulator_tokencards.txt', 'w') as file:
        file.write("2")

#ipns: k51qzi5uqu5dkr4uo4hxis4mw58i86aafbbq047m0k9k1ncv3q46jyap2zyfk0
#ipfs link port 5001 complete: http://127.0.0.1:5001/ipfs/bafybeidf7cpkwsjkq6xs3r6fbbxghbugilx3jtezbza7gua3k5wjixpmba/#/ipns/k51qzi5uqu5dkr4uo4hxis4mw58i86aafbbq047m0k9k1ncv3q46jyap2zyfk0   

class TokenID(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), nullable=False) 

class AValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), unique=True, nullable=False)  

class nValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), unique=True, nullable=False)  

class phiValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), unique=True, nullable=False) 

class IPNSHash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), unique=True, nullable=False) 

class QRCodeCustomer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(64), nullable=False)


def store_in_database(valueType,value):
    print(f"Attempting to store value {value} in the database for {valueType}")
    try:
        existing_value = valueType.query.filter_by(value=str(value)).first()
        if existing_value is None:
            print(f"Value {value} does not exist in the database for {valueType}. Creating new entry.")
            new_value = valueType(value=str(value)) 
            db.session.add(new_value)
            db.session.commit()
            print(f"Successfully stored value {value} in the database for {valueType}")
        else:
            print(f"Value {value} already exists in the database for {valueType}. Raising ValueError.")
            raise ValueError(f"Value {value} already exists in the database for {valueType}")
    except Exception as e:
        print(f"An error occurred while storing {value} in the database for {valueType}: {str(e)}. Raising Exception.")
        raise Exception(f"An error occurred while storing {value} in the database for {valueType}: {str(e)}")

def read_from_database(modelClass):
    print("We are in read_from_database")
    try:
        print("We are in try of read_from_database")
        record = modelClass.query.first()
        print(f"record is {record}")
        if record:
            return str(record.value) 
        else: 
            raise ValueError(f"No records found for {modelClass.__name__}")
    except Exception as e:
        raise ValueError(f"An error occurred while reading from {modelClass.__name__}: {str(e)}")

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')

@app.route('/setup', methods=['GET']) #this needs to be done with the creation of the account (not at the installation of the app)
def setup():
    n, phi = n_for_RSA()
    print(f"n is {n} and phi is {phi}")
    store_in_database(nValue,hex(n)[2:])
    store_in_database(phiValue,hex(phi)[2:])
    return "Success"

@app.route('/generate-token', methods=['GET'])
def generate_token():
    n = int(read_from_database(nValue),16)
    phi = int(read_from_database(phiValue),16)
    random_coprime = random_coprime_with_totient(n, phi)  
    tokenID_hex = hex(random_coprime)[2:]
    store_in_database(TokenID, tokenID_hex)

    return jsonify(tokenID=str(random_coprime))  # Send a JSON response


@app.route('/accumulate-token', methods=['POST'])
def accumulate_token():
    data = request.get_json()

    tokenID_str = data.get('tokenID', '')
    try:
        tokenID = int(tokenID_str)  
        
    except ValueError:
        return jsonify(error="Invalid tokenID value"), 400

    try:
        n_record = read_from_database(nValue)
        n = int(n_record,16)
        #check token validity
        if tokenID >= n or tokenID <= 0:
            return jsonify(error="tokenID is out of acceptable range"), 400
        
        # Fetch 'A' from the database
        a_record = AValue.query.first()
        if a_record:
            A = int(a_record.value,16)
        else:
            A = 2 

        A = rsa_accumulate(n, tokenID, A)
        if a_record:
            a_record.value = hex(A)[2:]
            with open('accumulator_tokencards.txt', 'w') as file:
                file.write(a_record.value)
            
        else:
            new_a_record = AValue(value=hex(A)[2:])
            db.session.add(new_a_record)
            with open('accumulator_tokencards.txt', 'w') as file:
                file.write(new_a_record.value)
        upload_file_to_ipfs('accumulator_tokencards.txt')
        
        db.session.commit() 

        return jsonify(success=True), 200
    except Exception as e:
        app.logger.error(f"Error in accumulate-token: {e}")
        return jsonify(error="Internal server error"), 500



@app.route('/verification-token', methods=['POST'])
def verify_token():
    try:
        token = request.json.get('tokenID_verify')
        print(f"We receive token {token} ")
        if token is None:
            return jsonify({"error": "TokenID missing from request"}), 400
    except Exception as e:
        return jsonify({"error": "Failed to extract token from request"}), 400
    
    try:
        # n_record = read_from_database('nValue')
        record1 = nValue.query.first()
        n_record = str(record1.value)
        print(f"n is {n_record}")
        # phi_record = read_from_database('phiValue')
        # a_record = read_from_database('AValue')
        record2 = phiValue.query.first()
        record3 = AValue.query.first()
        phi_record = str(record2.value)
        a_record = str(record3.value)
    except Exception as e:
        return jsonify({"error": "Failed to read from database"}), 500

    try:
        token_int = int(token, 16)
        n_modulus = int(n_record, 16)
        phi_modulus = int(phi_record, 16)
        A = int(a_record, 16)
    except ValueError as e:
        return jsonify({"error": "Invalid data format for conversion"}), 400

    try:
        if A is None or n_modulus is None:
            return jsonify({"error": "Accumulator values not found in the database"}), 500

        base = root_extraction(A, token_int, n_modulus, phi_modulus)
        verified = pow(base, token_int, n_modulus) == A
    except Exception as e:
        return jsonify({"error": "Error during verification computation"}), 500

    return jsonify({"verified": verified})

@app.route('/verification-token-qr-code', methods=['POST'])
def verify_token_qr_code():
    try:
        data = request.json
        token = data['qrCode']
        print(f"We receive token {token} ")
        if token is None:
            return jsonify({"error": "TokenID missing from request"}), 400
    except Exception as e:
        return jsonify({"error": "Failed to extract token from request"}), 400
    
    try:
        # n_record = read_from_database('nValue')
        record1 = nValue.query.first()
        n_record = str(record1.value)
        print(f"n is {n_record}")
        # phi_record = read_from_database('phiValue')
        # a_record = read_from_database('AValue')
        record2 = phiValue.query.first()
        record3 = AValue.query.first()
        phi_record = str(record2.value)
        a_record = str(record3.value)
    except Exception as e:
        return jsonify({"error": "Failed to read from database"}), 500

    try:
        token_int = int(token, 16)
        n_modulus = int(n_record, 16)
        phi_modulus = int(phi_record, 16)
        A = int(a_record, 16)
    except ValueError as e:
        return jsonify({"error": "Invalid data format for conversion"}), 400

    try:
        if A is None or n_modulus is None:
            return jsonify({"error": "Accumulator values not found in the database"}), 500

        base = root_extraction(A, token_int, n_modulus, phi_modulus)
        verified = pow(base, token_int, n_modulus) == A
    except Exception as e:
        return jsonify({"error": "Error during verification computation"}), 500

    return jsonify({"verified": verified})

@app.route('/spend-token', methods=['POST'])
def spend_token():
    try:
        tokenID = request.json.get('tokenID_spend')
        print(f"tokenID to spend is {tokenID}")
        if tokenID is None:
            return jsonify({"error": "TokenID missing from request"}), 400
    except Exception as e:
        return jsonify({"error": "Failed to extract token from request"}), 400

    #read from the database
    try:
        # n_record = read_from_database('nValue')
        # print(f"n is {n_record}")
        # a_record = read_from_database('AValue')
        # phi_record = read_from_database('phiValue')
        record1 = nValue.query.first()
        n_record = str(record1.value)
        record2 = phiValue.query.first()
        record3 = AValue.query.first()
        phi_record = str(record2.value)
        a_record = str(record3.value)

    except Exception as e:
        return jsonify({"error": "Failed to read from database"}), 500
    
    #conversion
    try:
        token_int = int(tokenID, 16)
        n_modulus = int(n_record, 16)
        phi_modulus = int(phi_record, 16)
        if token_int >= n_modulus or token_int <= 0:  # Validate tokenID is within an acceptable range
            return jsonify(error="tokenID is out of acceptable range"), 400
        A = int(a_record, 16)
    except ValueError as e:
        return jsonify({"error": "Invalid data format for conversion"}), 400

    try:
        if A is None or n_modulus is None:
            return jsonify({"error": "Accumulator values not found in the database"}), 500

        base = root_extraction(A, token_int, n_modulus, phi_modulus)
        verified = pow(base, token_int, n_modulus) == A
    except Exception as e:
        return jsonify({"error": "Error during verification computation"}), 500

    if verified:
        try:
            token_hex = tokenID.lower()
            token_record = TokenID.query.filter_by(value=token_hex).first()
            if token_record:
                print(f"token_record does exist and we are deleting it")
                db.session.delete(token_record)
                ## update accumulator in 
                a_record = AValue.query.first()
                a_record.value = hex(base)[2:]

                db.session.commit()
                with open('accumulator_tokencards.txt', 'w') as file:
                    file.write(a_record.value)
                upload_file_to_ipfs('accumulator_tokencards.txt')

                return jsonify({"success": "Token verified and spent successfully"}), 200
            
            else:
                return jsonify({"error": "TokenID not found in database"}), 404
        except Exception as e:
            return jsonify({"error": "Failed to delete token from database"}), 500
    else:
        return jsonify({"error": "Token verification failed"}), 400

@app.route('/store-token-customer', methods=['POST'])
def store_token():
    data = request.json
    tokenID = data['qrCode']
    try:
        store_in_database(QRCodeCustomer,tokenID)    
        return jsonify({'message': 'QR Code stored successfully'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to store QR Code'}), 500


if __name__ == '__main__':
    setup_app(app)
    app.run(debug=True, host='127.0.0.1', port=5000)


