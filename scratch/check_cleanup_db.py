import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend-scripts")))
import firebase_helper

def check():
    db = firebase_helper.init_firebase()
    
    # 1. auto_cleanup doc
    doc_ref = db.collection("system_config").document("auto_cleanup")
    doc = doc_ref.get()
    if doc.exists:
        print("auto_cleanup config:")
        print(doc.to_dict())
    else:
        print("auto_cleanup document does not exist!")

    # 2. scheduler doc
    doc_ref = db.collection("system_config").document("scheduler")
    doc = doc_ref.get()
    if doc.exists:
        print("scheduler config:")
        print(doc.to_dict())
    else:
        print("scheduler document does not exist!")

if __name__ == "__main__":
    check()
