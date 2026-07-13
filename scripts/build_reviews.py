import json
from collections import Counter

reviews = []
review_id = 1

def make_review(hotel_name, source_url, user, rating, date, content):
    global review_id
    r = {
        "id": f"ctrip_rpa_{review_id:04d}",
        "platform": "\u643a\u7a0bRPA",
        "source_url": source_url,
        "business_name": hotel_name,
        "business_type": "\u4f4f\u5bbf",
        "user": user if user else "Guest User",
        "rating": rating,
        "date": date,
        "content": content.strip()
    }
    review_id += 1
    return r

url1 = "https://www.trip.com/hotels/zhuhai-hotel-detail-110055851/holiday-inn-express-zhuhai-guishan-island-by-ihg/"
hotel1 = "\u667a\u9009\u5047\u65e5\u9152\u5e97"

reviews.append(make_review(hotel1, url1, "zhuifeng506", None, "2026-06-22",
    "Great for a family vacation! The hotel has a good location, offers pier transfers, and the staff are very enthusiastic. They pay attention to the details, which is a nice touch. They also have their own restaurant with pretty good food, and they can even prepare seafood for you!"))

reviews.append(make_review(hotel1, url1, "Guest User", None, "2026-06-16",
    "The hotel's location is incredibly convenient, less than 100 meters from the pier. We booked a sea-view room and the ocean view was absolutely delightful. The room was spacious and clean. The front desk staff, particularly Xiao Chen, was warm, attentive, and organized, leaving us with a great impression."))

reviews.append(make_review(hotel1, url1, "Guest User", None, "2026-01-02",
    "The room is spacious and quiet, and the bed is very soft - I slept soundly until morning. Every time I visit the island, I stay at this hotel. The service is professional, it's clean, and always a comfortable stay."))

url2 = "https://www.trip.com/hotels/zhuhai-hotel-detail-88744884/liyuanguixi-baysiade-sea-view-guesthouse/"
hotel2 = "\u91cc\u82d1\u00b7\u6842\u6c50\u6e7e\u7554"

reviews.append(make_review(hotel2, url2, "Guest User", None, "2024-12-20",
    "Pick-up service from the pier to the hotel, the room is clean and tidy, the sea view is unparalleled, the service is excellent, and it is a very pleasant experience"))

reviews.append(make_review(hotel2, url2, "Guest User", None, "2024-12-18",
    "The room is very clean, and there is still a fragrance when you enter the room. The environment is very nice and very photogenic. I recommend it to friends who want to take photos!"))

reviews.append(make_review(hotel2, url2, "sheard", None, "2024-11-24",
    "It is understandable that accommodation on Guishan Island was more expensive than usual on Saturdays. The Holiday Inn on Guishan Island is much better than this B&B that costs close to 900 a night in terms of location, room size and service level."))

url3 = "https://www.trip.com/hotels/zhuhai-hotel-detail-71649761/zhuhai-guishan-island-yuanben-guishe/"
hotel3 = "\u5143\u672c\u6842\u820d"

reviews.append(make_review(hotel3, url3, "Guest User", 2.0, "2023-08-21",
    "Environment: Although it is a B&B, the environment is too bad. Facilities: messy and miscellaneous furnishings. Hygiene: dust on the table and bed. Service: not much. The price of the hotel is ridiculously high."))

reviews.append(make_review(hotel3, url3, "Guest User", 5.0, "2023-07-21",
    "I booked a two-bedroom apartment with one living room. Overall, it had a musty smell. The sister at the front desk is very nice. What needs to be complained about is that there were three little cats in the bathroom."))

reviews.append(make_review(hotel3, url3, "Guest User", 10.0, "2026-04-17",
    "\u6c11\u5bbf\u74b0\u5883\u6e29\u99a8\u96c5\u81f4\uff0c\u4e7e\u6de8\u6574\u6f54\u7121\u7570\u5473\uff0c\u9084\u514d\u8cbb\u63a5\u9001\u78bc\u982d\u3002\u623f\u6771\u71b1\u60c5\u8cbc\u5fc3\uff0c\u7d30\u7bc0\u5230\u4f4d\uff0c\u5c45\u4f4f\u611f\u50cf\u5bb6\u4e00\u6a23\u8212\u670d\uff0c\u4f4d\u7f6e\u4fbf\u5229\u5b89\u975c\uff0c\u9ad4\u9a57\u8d85\u68d2\uff0c\u63a8\u85a6\u5165\u4f4f\uff01"))

reviews.append(make_review(hotel3, url3, "Guest User", 7.5, "2026-02-25",
    "\u9152\u5e97\u4f4d\u65bc\u534a\u5c71\u4e0a\uff0c\u666f\u8272\u662f\u4e0d\u932f\u7684\uff0c\u6c11\u5bbf\u6709\u78bc\u982d\u4f86\u56de\u63a5\u9001\u3002\u5169\u500b\u623f\u9593\u7684\u6d17\u624b\u9593\u90fd\u6709\u975e\u5e38\u6fc3\u7684\u81ed\u5473\uff0c\u554f\u5546\u5bb6\u62ff\u4e86\u9999\u85b0\u5674\u4e86\u624d\u52c9\u5f37\u80fd\u4f4f\u3002"))

reviews.append(make_review(hotel3, url3, "RainJJJ", 10.0, "2026-04-19",
    "\u5728\u534a\u5c71\u8170\u7684\u6c11\u5bbf\uff0c\u8001\u677f\u6703\u958b\u8eca\u4f86\u78bc\u982d\u63a5\u9001\uff0c\u623f\u9593\u4e7e\u6de8\u885e\u751f\u3002\u6211\u5011\u662f4\u6708\u4e2d\u65ec\u53bb\u7684\u6842\u5c71\u5cf6\uff0c\u4eba\u4e0d\u662f\u5f88\u591a\uff0c\u5cf6\u4e0a\u98a8\u666f\u5f88\u6f02\u4eae\uff0c\u7f8e\u98df\u4ee5\u6d77\u9bae\u70ba\u4e3b\u3002"))

reviews.append(make_review(hotel3, url3, "Guest User", 10.0, "2026-03-05",
    "\u51fa\u9580\u5c31\u770b\u5230\u6d77\uff0c\u4e00\u4e0b\u8239\u5e97\u5bb6\u5c31\u958b\u8457\u8eca\u4f86\u63a5\u4e86\uff0c\u4f4f\u5728\u534a\u5c71\u4e0a\uff0c\u7a7a\u6c23\u6e05\u6d17\u3002\u9ad4\u9a57\u975e\u5e38\u597d\uff0c\u4e0b\u6b21\u9084\u6703\u518d\u9078\u64c7\u5143\u672c"))

reviews.append(make_review(hotel3, url3, "Anonymous User", 10.0, "2026-04-18",
    "\u885e\u751f\u4e7e\u6de8\uff0c\u7ba1\u5bb6\u670d\u52d9\u71b1\u60c5\uff0c\u6c11\u5bbf\u666f\u8272\u4e5f\u597d\u770b\uff0c\u96e2\u611b\u6c11\u8def\u5f88\u8fd1\uff0c\u6709\u64fa\u6e21\u8eca\u63a5\u9001\u78bc\u982d\uff0c\u60c5\u4fb6\u51fa\u904a\uff0c\u63a8\u85a6"))

reviews.append(make_review(hotel3, url3, "Duoduoer", 10.0, "2026-04-11",
    "\u9152\u5e97\u74b0\u5883\u4e0d\u932f \u9580\u53e3\u62cd\u7167\u5341\u5206\u51fa\u7247 \u4f86\u56de\u6709\u63a5\u9001 \u670d\u52d9\u614b\u5ea6\u975e\u5e38\u597d \u5f88\u71b1\u60c5 \u633a\u4e0d\u932f\u7684"))

reviews.append(make_review(hotel3, url3, "Guest User", 10.0, "2026-04-21",
    "\u5468\u570d\u74b0\u5883\u7279\u5225\u6f02\u4eae\uff0c\u597d\u591a\u675c\u9d51\u82b1\uff0c\u6c11\u5bbf\u80fd\u770b\u5230\u65e5\u843d\uff0c\u623f\u9593\u4e5f\u4e7e\u6de8\uff0c\u670d\u52d9\u4e5f\u597d"))

url4 = "https://www.trip.com/hotels/zhuhai-hotel-detail-85243453/xianyunju-boutique-bb-zhuhai-guishan-island-shop/"
hotel4 = "\u95f2\u4e91\u5c45\u7cbe\u54c1\u6c11\u5bbf"

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-02-15",
    "The owner upgraded us to a sea-view room. The location was excellent, very close to the pier, and there were restaurants downstairs. It was also very good value for money."))

reviews.append(make_review(hotel4, url4, "Anonymous User", 2.0, "2025-05-02",
    "Ctrip wrote that there is a pick-up service, but when I called, no one came to pick me up. The hotel's kettle was rusty. The toilet is very noisy at night. The service attitude was very bad. The room is very bad, it's a rental house, not a hotel or a B&B."))

reviews.append(make_review(hotel4, url4, "Guest User", 2.0, "2024-04-06",
    "Extremely dissatisfied with this stay. 1) The location is halfway up the mountain! 2) Poor hygiene. 3) We booked a three-bedroom villa, but it was actually a four-bedroom villa sold separately. 4) The room door was locked after 9:00 PM and there was no room key. 5) Security concerns with master key near entrance."))

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-06-11",
    "\u6842\u5c71\u5cf6\u7684\u6d77\u6c34\u662f\u78a7\u7da0\u8272\u7684\uff0c\u5f88\u7f8e\u3002\u6c11\u5bbf\u96e2\u78bc\u982d\u5f88\u8fd1\uff0c\u8d70\u8def\u5e7e\u5206\u9418\u5c31\u5230\u4e86\uff0c\u6709\u96fb\u68af\u7279\u5225\u65b9\u4fbf\u3002\u6a13\u4e0b\u5f88\u591a\u9910\u5ef3\uff0c\u6d77\u6d0b\u5e02\u5834\u50f9\u683c\u660e\u78bc\u6a19\u50f9\u3002\u885e\u751f\u4e7e\u6de8\uff0c\u5e8a\u92ea\u6574\u9f4a\uff0c\u7ba1\u5bb6\u670d\u52d9\u597d\u3002\u74b0\u5883\u8212\u9069\uff0c\u63a8\u85a6\u5165\u4f4f"))

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-06-06",
    "\u5929\u6c23\u5f88\u597d\uff0c\u51fa\u884c\u6210\u672c\u4eba\u5747\u4e0d\u8cb4\uff0c100\u591a\u7684\u6c11\u5bbf\u4e7e\u6de8\u885e\u751f\uff0c\u5168\u7a0b\u7ba1\u5bb6\u63a5\u5f85\u670d\u52d9\uff0c\u6709\u547c\u5fc5\u61c9\uff0c\u6c11\u5bbf\u6574\u9ad4\u74b0\u5883\u5f88\u597d\uff0c\u96e2\u78bc\u982d\u4e5f\u5f88\u8fd1\uff0c\u5403\u98ef\u4e5f\u65b9\u4fbf\uff0c\u503c\u5f97\u4e8c\u5237"))

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-05-31",
    "\u597d \u885e\u751f\uff1a\u597d \u74b0\u5883\uff1a\u597d \u670d\u52d9\uff1a\u597d\u597d \u8a2d\u65bd\uff1a\u597d\u9152\u5e97\u9760\u8fd1\u6d77\u908a\uff0c\u4e0b\u6a13\u5c31\u662f\u6d77\u9bae\u5e02\u5834\uff0c\u9084\u6709\u5f88\u591a\u4fbf\u5229\u5e97\uff0c\u96e2\u78bc\u982d\u8fd1"))

reviews.append(make_review(hotel4, url4, "\u4e38\u5b50\u98db\u98db", 8.5, "2026-05-27",
    "\u51fa\u78bc\u982d\u5de6\u8f49\uff0c\u5927\u6982\u4e24\u4e09\u767e\u7c73\u5c31\u5230\uff0c\u4f4d\u7f6e\u4e0d\u7528\u8d70\u4e0a\u6ce2\u8def\uff0c\u6a13\u4e0b\u5c31\u6709\u98df\u5e02\uff0c\u5c0d\u9762\u6d77\u9bae\u5e02\u5834\uff0c\u5468\u908a\u90fd\u6709\u5c0f\u9152\u9928\u548c\u4fbf\u5229\u5e97"))

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-03-12",
    "\u525b\u958b\u59cb\u8a02\u7684\u7279\u50f9\u623f\uff0c\u4f86\u5230\u5c0d\u6bd4\u4e86\u4e00\u4e0b\u6d77\u666f\u623f\uff0c\u679c\u65b7\u9078\u64c7\u88dc\u5dee\u50f9\u5165\u4f4f\uff0c\u623f\u9593\u63a1\u5149\u548c\u8996\u91ce\u90fd\u5f88\u597d\uff0c\u4e7e\u6de8\u6574\u6f54\u3001\u8a2d\u65bd\u9f4a\u5168\u597d\u7528\uff0c\u74b0\u5883\u5b89\u975c\u96c5\u81f4\u3002\u524d\u53f0\u71b1\u60c5\u5468\u5230\uff0c\u8fa6\u7406\u5165\u4f4f\u9000\u623f\u90fd\u5f88\u5feb\uff0c\u6574\u9ad4\u9ad4\u9a57\u8d85\u51fa\u9810\u671f\uff0c\u5f37\u70c8\u63a8\u85a6\uff01"))

reviews.append(make_review(hotel4, url4, "Guest User", 10.0, "2026-03-06",
    "\u6c11\u5bbf\u5916\u89c0\u53e4\u6a38\u5178\u96c5\uff0c\u5167\u90e8\u88dd\u4fee\u7cbe\u81f4\u7528\u5fc3\u3002\u623f\u9593\u7684\u9694\u97f3\u6548\u679c\u8d85\u68d2\uff0c\u665a\u4e0a\u7761\u5f97\u7279\u5225\u5b89\u7a69\u3002\u623f\u9593\u63a1\u5149\u5f88\u597d\uff0c\u5fc3\u60c5\u90fd\u683c\u5916\u8212\u66a2\u3002\u74b0\u5883\u6e05\u5e7d\uff0c\u9060\u96e2\u57ce\u5e02\uff0c\u662f\u653e\u9b06\u8eab\u5fc3\u7684\u597d\u53bb\u8655\u3002\u6574\u9ad4\u9ad4\u9a57\u611f\u5341\u8db3\uff0c\u5fc5\u9808\u4e94\u661f\u597d\u8a55\uff01"))

url5 = "https://www.trip.com/hotels/zhuhai-hotel-detail-82635525/sunny-hotel-zhuhai-guishan-island/"
hotel5 = "\u9a7f\u65c5\u9633\u5149\u6c11\u5bbf"

reviews.append(make_review(hotel5, url5, "Anonymous User", 8.0, "2024-07-06",
    "very good"))

reviews.append(make_review(hotel5, url5, "Haidayezishu", 7.7, "2026-06-28",
    "\u8c6a\u83ef\u6d77\u666f\u5927\u5e8a\u623f\u4f4d\u65bc3/5\u6a13\uff0c\u9700\u8981\u722c\u6a13\u68af\uff0c\u6240\u4f4f\u7684\u623f\u9593\uff0c\u7a7a\u8abf\u4e0d\u88fd\u51b7\uff0c\u566a\u8072\u5f88\u5927\u3002\u5ec1\u6240\u96d6\u7136\u4e7e\u6fdf\u5206\u96e2\uff0c\u4f46\u6dcb\u6d74\u9593\u904e\u5c0f\uff0c\u4e14\u9580\u95dc\u4e0d\u4e0a\u3002"))

reviews.append(make_review(hotel5, url5, "QookuerQooer", 10.0, "2026-06-23",
    "\u8a2d\u65bd\uff1a\u5f88\u597d\uff0c\u9f4a\u5168 \u885e\u751f\uff1a\u4e7e\u6de8 \u74b0\u5883\uff1a\u975e\u5e38\u597d\uff0c\u5c0d\u7740\u4f36\u4ec3\u6d0b \u670d\u52d9\uff1a\u975e\u5e38\u597d"))

reviews.append(make_review(hotel5, url5, "shshiris", 7.5, "2026-02-22",
    "\u56e0\u70ba\u4ecd\u7136\u4fc2\u65b0\u5e74\u671f\u9593\uff0c\u5927\u90e8\u5206\u6c11\u5bbf\u4f9b\u61c9\u7e4a\u5f35\u3002\u8a2d\u5099\u7576\u7136\u5514\u53ef\u4ee5\u540c\u9152\u5e97\u76f8\u6bd4\uff0c\u4f46\u885e\u751f\u60c5\u6cc1\u6eff\u610f\uff0c\u6d17\u624b\u9593\u4e7e\u6fdf\u5206\u9694\uff0c\u53bb\u6c34\u7121\u554f\u984c\uff0c\u71b1\u6c34\u4f9b\u61c9\u7a69\u5b9a\u3002\u4f4d\u7f6e\u975e\u5e38\u65b9\u4fbf\uff0c\u4f46\u6c11\u5bbf\u4fc2\u7121\u9418\uff0c\u6240\u4ee5\u8981\u722c\u6a13\u68af\u4e0a6\u6a13\uff0c\u4f46\u9732\u53f0\u53ef\u4ee5\u671b\u898b\u7121\u6575\u5927\u6d77\u666f\u3002\u6574\u9ad4\u7b97\u6eff\u610f\u3002"))

reviews.append(make_review(hotel5, url5, "Guest User", 9.0, "2026-04-23",
    "\u96e2\u78bc\u982d\u8fd1\uff0c\u6027\u50f9\u6bd4\u4e0d\u932f\u3002\u5468\u908a\u5403\u98ef\u5f88\u65b9\u4fbf\uff0c\u96e2\u5e7e\u500b\u7db2\u7d05\u5e97\u90fd\u5f88\u8fd1\u3002\u9019\u500b\u50f9\u683c\u5728\u6842\u5c71\u5cf6\u7b97\u6027\u50f9\u6bd4\u5f88\u9ad8\u7684\u4e86\uff0c\u63a8\u85a6\u5165\u4f4f\u3002"))

reviews.append(make_review(hotel5, url5, "Balabalahahaha", 8.5, "2026-05-04",
    "\u51fa\u4f86\u73a9\u6574\u9ad4\u611f\u89ba\u4e0d\u932f\uff0c\u8a2d\u65bd\u53ef\u4ee5\u66f4\u5b8c\u5584\u66f4\u65b0\uff0c\u5730\u7406\u4f4d\u7f6e\u9084\u662f\u53ef\u4ee5\u7684 \u885e\u751f\uff1a\u53ef\u4ee5\u66f4\u597d \u670d\u52d9\uff1a\u9084\u662f\u4e0d\u932f\u7684 \u74b0\u5883\uff1a\u51fa\u4f86\u73a9\u5c31\u662f\u8981\u958b\u5fc3\u7684\u54c8\u54c8\u54c8"))

reviews.append(make_review(hotel5, url5, "Guest User", 7.2, "2026-06-25",
    "\u5929\u6c23\u592a\u71b1\u4e0d\u5efa\u8b70\u9078\u6a13\u9802\u7684\u623f\uff0c\u767d\u5929\u5de8\u71b1\uff0c\u66ec\u5f97\u5230\u665a\u4e0a\u7246\u58c1\u4e5f\u90fd\u662f\u71b1\u7684\uff0c\u7a7a\u8abf\u958b16\u5ea6\u958b\u4e86\u5f88\u4e45\u6eab\u5ea6\u4e5f\u6c92\u964d\u4e0b\u4f86\uff0c\u5f8c\u9762\u6253\u96fb\u8a71\u554f\u623f\u6771\u8aaa\u8981\u958b20\u5ea6\u624d\u884c"))

reviews.append(make_review(hotel5, url5, "luojiabin", 10.0, "2026-01-26",
    "\u9019\u6b21\u96d9\u5e8a\u623f\u548c\u5927\u5e8a\u623f\u4e4b\u9593\uff0c\u96d9\u5e8a\u623f\u66f4\u4fbf\u5b9c\uff0c\u4f4f\u8d77\u4f86\u7684\u6027\u50f9\u6bd4\u6bd4\u8f03\u5212\u7b97\uff0c\u96d6\u7136\u6211\u8a02\u7684\u662f\u57ce\u666f\u623f\uff0c\u4f46\u662f\u670d\u52d9\u4eba\u54e1\u7684\u63a5\u5f85\u614b\u5ea6\u4ee5\u53ca\u5404\u65b9\u9762\u90fd\u6bd4\u8f03\u6eff\u610f"))

reviews.append(make_review(hotel5, url5, "Guest User", 5.2, "2025-12-01",
    "\u98a8\u666f\u623f\u9593\u885e\u751f\u74b0\u5883\u9084\u53ef\u4ee5\uff0c\u4f46\u662f\u4e0d\u9694\u97f3\uff0c\u4e00\u5927\u65e9\u7684\u592a\u5435\u4e86\uff0c7\u9ede\u591a\u5c31\u65bd\u5de5\uff0c\u6839\u672c\u6c92\u6cd5\u7761\u89ba\u3002\u767c\u6d88\u606f\u554f\u70ba\u4ec0\u9ebc\u9019\u9ebc\u5435\u60f3\u8acb\u89e3\u6c7a\u4e00\u4e0b\u4e5f\u4e0d\u56de"))

output_path = r"E:\珠海桂山岛案例\数据采集\raw\ctrip_rpa_reviews.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(reviews, f, ensure_ascii=False, indent=2)

hotel_counts = Counter(r["business_name"] for r in reviews)
print(f"Total reviews from fetch_content: {len(reviews)}")
for h, c in hotel_counts.items():
    print(f"  {h}: {c} reviews")
