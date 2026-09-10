import time
import requests

API_URL = "http://127.0.0.1:8000/api/documents"

def run():
    print("Uploading document...")
    with open("data/uploads/ea6b6a07-6dc7-4ed2-b127-448f88bb600d.pdf", "rb") as f:
        res = requests.post(f"{API_URL}/upload", files={"file": f})
    
    if not res.ok:
        print("Upload failed:", res.text)
        return
        
    doc_id = res.json()["document_id"]
    print("Document uploaded, ID:", doc_id)
    
    print("Waiting for processing to complete...")
    while True:
        status_res = requests.get(f"{API_URL}/{doc_id}/status")
        if not status_res.ok:
            print("Status fetch failed:", status_res.text)
            return
            
        data = status_res.json()
        print(f"Status: {data['status']} - Progress: {data.get('progress', 0)}%")
        if data["status"] == "ready":
            break
        elif data["status"] == "failed":
            print("Processing failed!")
            return
            
        time.sleep(5)
        
    print("Document ready! Sending chat request...")
    chat_res = requests.post(f"{API_URL}/{doc_id}/chat", json={"question": "What are the relaxations in building bylaws?"})
    
    if not chat_res.ok:
        print("Chat failed:", chat_res.text)
        return
        
    print("Chat successful!")

if __name__ == "__main__":
    run()
