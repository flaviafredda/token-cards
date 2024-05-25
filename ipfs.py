import requests
import tarfile
import ast


def extract_and_save_text_from_tar(tar_path, filename):
    # Open the tar archive in read mode
    with tarfile.open(tar_path, 'r') as tar:
        # Iterate over each member in the tar archive
        for member in tar.getmembers():
            # Check if the current member is a file
            if member.isfile():
                # Extract and read the content of the file
                file_content = tar.extractfile(member).read()
                # Assuming the file content is in a text-based format, decode it
                text = file_content.decode('utf-8')
                # Save the file name and its content
                with open(filename, 'w') as file:
                    file.write(text)


def publish_on_ipns(hash):
    url = f'http://127.0.0.1:5001/api/v0/name/publish'
    params = {
        'arg': hash,
    }
    try:
        response = requests.post(url, params=params, allow_redirects=True)
        if response.status_code == 200:
            print(response.text)  # Print the text of the response
            res_dict = ast.literal_eval(response.text)
            return res_dict
        else:
            print(f"Failed to get IPNS name with status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def upload_file_to_ipfs(filename):
    url = 'http://127.0.0.1:5001/api/v0/add'
    files = {'file': (filename, open(filename, 'rb'))}  # Open the file in binary mode

    try:
        response = requests.post(url, files=files)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("File uploaded successfully.")
            print(response.text)  # Print the text of the response
            res_dict = ast.literal_eval(response.text)
            d= publish_on_ipns(res_dict["Hash"])
            res_dict["ipns"] = d["Name"]
            return res_dict 
        else:
            print("Failed to upload file with status code:", response.status_code)
    except Exception as e:
        print("An error occurred:", str(e))
    finally:
        files['file'][1].close()  # Make sure to close the file after uploading


def download_file_from_ipfs(output_filename, arg):
    url = f'http://127.0.0.1:5001/api/v0/get'
    params = {
        'arg': arg,
        'output': output_filename
    }

    try:
        response = requests.post(url, params=params, allow_redirects=True)
        
        # Check if the request was successful
        if response.status_code == 200:
            try:
                # Save the content to a file
                with open(output_filename+".tar", 'wb') as file:
                    file.write(response.content)
                print(f"File {output_filename}.tar downloaded successfully.")
            except Exception as e:
                print(f"An error occurred while saving the file: {str(e)}")
                return

            try:
                print(f"Extracting {output_filename}.tar...")
                extract_and_save_text_from_tar(output_filename+".tar",output_filename)
                print(f"{output_filename} is ready")
            except Exception as e:
                print(f"An error occurred while extracting the file: {str(e)}")
        else:
            print(f"Failed to download file with status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Example usage:
# download_file('text.sh')


# Example usage:
# upload_file_to_server('test.sh')
# Example response:
# {"Name":"test.sh","Hash":"Qmd4UXZ8MkL4ffdA7x8FbjCVRhD3XTkYSmbYGLtPe1X4je","Size":"182"}

if __name__ == "__main__":
    res = upload_file_to_ipfs('ciao.txt')
    for key, value in res.items():
        print(f"{key}: {value}")
    download_file_from_ipfs("test", res["Hash"])
