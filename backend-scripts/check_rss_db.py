import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import firebase_helper

def main():
    db = firebase_helper.init_firebase()
    
    print("=== CATEGORIES ===")
    cat_doc = db.collection("system_config").document("categories").get()
    if cat_doc.exists:
        print(cat_doc.to_dict())
    else:
        print("Categories document does not exist!")
        
    print("\n=== RSS SOURCES ===")
    sources_ref = db.collection("rss_sources")
    docs = sources_ref.stream()
    for doc in docs:
        print(f"Doc ID: {doc.id} -> {doc.to_dict()}")

if __name__ == "__main__":
    main()
