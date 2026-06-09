import os
import sys

# Çalışma dizinini backend-scripts olarak ayarlayalım
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(base_dir, "backend-scripts")
os.chdir(backend_dir)
sys.path.append(backend_dir)

from fetcher import load_config
import auto_cleanup

def test_jaccard_on_recent():
    # Test case 1: Very similar titles
    t1 = "Google, Gemini için yeni özellikler sundu"
    t2 = "Google Gemini için yeni özellikler duyurdu"
    sim = auto_cleanup.check_mathematical_similarity(t1, t2)
    print(f"Test 1: '{t1}' vs '{t2}'")
    print(f"  Word set 1: {auto_cleanup.get_word_set(t1)}")
    print(f"  Word set 2: {auto_cleanup.get_word_set(t2)}")
    print(f"  Is similar? {sim}")
    
    # Test case 2: Slightly different, but close
    t3 = "Nvidia RTX 5090 ekran kartı tanıtıldı"
    t4 = "Nvidia RTX 5090 özellikleri sızdırıldı"
    sim2 = auto_cleanup.check_mathematical_similarity(t3, t4)
    print(f"Test 2: '{t3}' vs '{t4}'")
    print(f"  Is similar? {sim2}")

    # Test case 3: Totally different
    t5 = "Apple yeni Macbook modelini tanıttı"
    t6 = "SpaceX uzaya yeni roket gönderdi"
    sim3 = auto_cleanup.check_mathematical_similarity(t5, t6)
    print(f"Test 3: '{t5}' vs '{t6}'")
    print(f"  Is similar? {sim3}")

if __name__ == "__main__":
    test_jaccard_on_recent()
