from scrapling import StealthyFetcher

def test_linkedin():
    fetcher = StealthyFetcher()
    # جربنا هاد الـ URL اللي كيعطي الـ HTML ديال الكارطات
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Python%20Developer&location=Morocco"
    
    print(f"🔍 Fetching: {url} ...")
    response = fetcher.fetch(url)
    
    # شوف واش جاب الـ HTML ولا لا
    print(f"Status: {response.status}")
    
    # قلب على كاع الـ <li> اللي فيهم كلاس ديال Job Card
    # LinkedIn كيبدلو هاد الكلاسات بزاف، هادو هما المشهورين حاليا:
    job_cards = response.css('li') # نجربو نجبدو كاع الـ List items
    print(f"Total <li> items found: {len(job_cards)}")
    
    # طبع أول 500 حرف من الـ HTML باش نشوفو شنو فيه
    print("\n--- HTML Snippet ---")
    print(response.text[:500])

if __name__ == "__main__":
    test_linkedin()