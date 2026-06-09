import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend-scripts")))
import firebase_helper

def check():
    db = firebase_helper.init_firebase()
    doc_ref = db.collection("system_config").document("site_settings")
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        print("site_settings keys:")
        for k, v in data.items():
            # Hide the actual secret values but show the keys and whether they are set
            val_preview = str(v)[:10] + "..." if v else "None"
            print(f"- {k}: {val_preview} (length={len(str(v)) if v else 0})")
    else:
        print("site_settings document does not exist!")

if __name__ == "__main__":
    check()
