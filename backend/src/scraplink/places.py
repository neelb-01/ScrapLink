"""Where lots and businesses are: a fixed list of towns, so a seller picks one instead of typing.

Every state and union territory, through its capital and its main industrial and scrap-trading
towns (Alang, Mandi Gobindgarh, Moradabad, Jamnagar and so on), each at its town centre. A seller
outside these picks the nearest one; exact pickup points are still given when a pickup is booked.
A geocoder replaces the list later.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from .routing import Point, distance_metres


@dataclass(frozen=True)
class Place:
    code: str
    name: str
    state: str
    latitude: float
    longitude: float

    @property
    def point(self) -> Point:
        return (self.latitude, self.longitude)


PLACES: dict[str, Place] = {
    p.code: p
    for p in (
        # Andaman and Nicobar Islands
        Place("port_blair", "Port Blair", "Andaman and Nicobar Islands", 11.6683, 92.7378),
        # Andhra Pradesh
        Place("guntur", "Guntur", "Andhra Pradesh", 16.3008, 80.4428),
        Place("kurnool", "Kurnool", "Andhra Pradesh", 15.8300, 78.0500),
        Place("nellore", "Nellore", "Andhra Pradesh", 14.4431, 79.9861),
        Place("tirupati", "Tirupati", "Andhra Pradesh", 13.6355, 79.4236),
        Place("vijayawada", "Vijayawada", "Andhra Pradesh", 16.5144, 80.6192),
        Place("visakhapatnam", "Visakhapatnam", "Andhra Pradesh", 17.6939, 83.2922),
        # Arunachal Pradesh
        Place("itanagar", "Itanagar", "Arunachal Pradesh", 27.1000, 93.6200),
        # Assam
        Place("dibrugarh", "Dibrugarh", "Assam", 27.4800, 95.0000),
        Place("guwahati", "Guwahati", "Assam", 26.1722, 91.7458),
        Place("silchar", "Silchar", "Assam", 24.8200, 92.8000),
        # Bihar
        Place("bhagalpur", "Bhagalpur", "Bihar", 25.2500, 87.0000),
        Place("gaya", "Gaya", "Bihar", 24.7500, 85.0100),
        Place("muzaffarpur", "Muzaffarpur", "Bihar", 26.1209, 85.3647),
        Place("patna", "Patna", "Bihar", 25.5939, 85.1375),
        # Chandigarh
        Place("chandigarh", "Chandigarh", "Chandigarh", 30.7333, 76.7797),
        # Chhattisgarh
        Place("bhilai", "Bhilai", "Chhattisgarh", 21.2100, 81.3800),
        Place("bilaspur_cg", "Bilaspur", "Chhattisgarh", 22.0900, 82.1500),
        Place("korba", "Korba", "Chhattisgarh", 22.3500, 82.6800),
        Place("raipur", "Raipur", "Chhattisgarh", 21.2444, 81.6306),
        # Dadra and Nagar Haveli and Daman and Diu
        Place("daman", "Daman", "Dadra and Nagar Haveli and Daman and Diu", 20.4200, 72.8500),
        Place("silvassa", "Silvassa", "Dadra and Nagar Haveli and Daman and Diu", 20.2708, 73.0050),
        # Delhi
        Place("delhi", "Delhi", "Delhi", 28.6139, 77.2089),
        # Goa
        Place("panaji", "Panaji", "Goa", 15.4989, 73.8278),
        Place("vasco_da_gama", "Vasco da Gama", "Goa", 15.3981, 73.8111),
        # Gujarat
        Place("ahmedabad", "Ahmedabad", "Gujarat", 23.0225, 72.5714),
        Place("alang", "Alang", "Gujarat", 21.3975, 72.1775),
        Place("ankleshwar", "Ankleshwar", "Gujarat", 21.6264, 73.0152),
        Place("bhavnagar", "Bhavnagar", "Gujarat", 21.7600, 72.1500),
        Place("gandhidham", "Gandhidham", "Gujarat", 23.0800, 70.1300),
        Place("jamnagar", "Jamnagar", "Gujarat", 22.4700, 70.0700),
        Place("morbi", "Morbi", "Gujarat", 22.8200, 70.8300),
        Place("rajkot", "Rajkot", "Gujarat", 22.3000, 70.7833),
        Place("surat", "Surat", "Gujarat", 21.2050, 72.8400),
        Place("vadodara", "Vadodara", "Gujarat", 22.3000, 73.2000),
        Place("vapi", "Vapi", "Gujarat", 20.3720, 72.9170),
        # Haryana
        Place("ambala", "Ambala", "Haryana", 30.3800, 76.7800),
        Place("faridabad", "Faridabad", "Haryana", 28.4211, 77.3078),
        Place("gurugram", "Gurugram", "Haryana", 28.4560, 77.0290),
        Place("hisar", "Hisar", "Haryana", 29.1500, 75.7000),
        Place("panipat", "Panipat", "Haryana", 29.3875, 76.9700),
        Place("rohtak", "Rohtak", "Haryana", 28.8909, 76.5796),
        Place("sonipat", "Sonipat", "Haryana", 28.9900, 77.0220),
        Place("yamunanagar", "Yamunanagar", "Haryana", 30.1330, 77.2880),
        # Himachal Pradesh
        Place("baddi", "Baddi", "Himachal Pradesh", 30.9280, 76.7960),
        Place("shimla", "Shimla", "Himachal Pradesh", 31.1033, 77.1722),
        # Jammu and Kashmir
        Place("jammu", "Jammu", "Jammu and Kashmir", 32.7300, 74.8700),
        Place("srinagar", "Srinagar", "Jammu and Kashmir", 34.0900, 74.7900),
        # Jharkhand
        Place("bokaro", "Bokaro Steel City", "Jharkhand", 23.6700, 86.1500),
        Place("dhanbad", "Dhanbad", "Jharkhand", 23.7998, 86.4305),
        Place("jamshedpur", "Jamshedpur", "Jharkhand", 22.7925, 86.1842),
        Place("ranchi", "Ranchi", "Jharkhand", 23.3600, 85.3300),
        # Karnataka
        Place("ballari", "Ballari", "Karnataka", 15.1397, 76.9187),
        Place("belagavi", "Belagavi", "Karnataka", 15.8500, 74.5000),
        Place("bengaluru", "Bengaluru", "Karnataka", 12.9716, 77.5946),
        Place("hubballi", "Hubballi", "Karnataka", 15.3502, 75.1376),
        Place("kalaburagi", "Kalaburagi", "Karnataka", 17.3290, 76.8250),
        Place("mangaluru", "Mangaluru", "Karnataka", 12.9141, 74.8560),
        Place("mysuru", "Mysuru", "Karnataka", 12.3086, 76.6531),
        # Kerala
        Place("alappuzha", "Alappuzha", "Kerala", 9.4981, 76.3388),
        Place("kannur", "Kannur", "Kerala", 11.8745, 75.3704),
        Place("kochi", "Kochi", "Kerala", 9.9816, 76.2999),
        Place("kollam", "Kollam", "Kerala", 8.8932, 76.6141),
        Place("kottayam", "Kottayam", "Kerala", 9.5916, 76.5222),
        Place("kozhikode", "Kozhikode", "Kerala", 11.2588, 75.7804),
        Place("malappuram", "Malappuram", "Kerala", 11.0510, 76.0711),
        Place("palakkad", "Palakkad", "Kerala", 10.7867, 76.6548),
        Place("thiruvananthapuram", "Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
        Place("thrissur", "Thrissur", "Kerala", 10.5276, 76.2144),
        # Ladakh
        Place("leh", "Leh", "Ladakh", 34.1529, 77.5773),
        # Lakshadweep
        Place("kavaratti", "Kavaratti", "Lakshadweep", 10.5700, 72.6400),
        # Madhya Pradesh
        Place("bhopal", "Bhopal", "Madhya Pradesh", 23.2589, 77.4125),
        Place("gwalior", "Gwalior", "Madhya Pradesh", 26.2125, 78.1775),
        Place("indore", "Indore", "Madhya Pradesh", 22.7186, 75.8550),
        Place("jabalpur", "Jabalpur", "Madhya Pradesh", 23.1667, 79.9333),
        Place("pithampur", "Pithampur", "Madhya Pradesh", 22.6197, 75.6933),
        Place("ujjain", "Ujjain", "Madhya Pradesh", 23.1700, 75.7900),
        # Maharashtra
        Place("bhiwandi", "Bhiwandi", "Maharashtra", 19.2967, 73.0631),
        Place(
            "chhatrapati_sambhajinagar",
            "Chhatrapati Sambhajinagar",
            "Maharashtra",
            19.8800,
            75.3200,
        ),
        Place("jalna", "Jalna", "Maharashtra", 19.8410, 75.8864),
        Place("kolhapur", "Kolhapur", "Maharashtra", 16.6917, 74.2333),
        Place("mumbai", "Mumbai", "Maharashtra", 19.0761, 72.8775),
        Place("nagpur", "Nagpur", "Maharashtra", 21.1458, 79.0882),
        Place("nashik", "Nashik", "Maharashtra", 19.9975, 73.7898),
        Place("navi_mumbai", "Navi Mumbai", "Maharashtra", 19.0330, 73.0297),
        Place("pune", "Pune", "Maharashtra", 18.5211, 73.8553),
        Place("solapur", "Solapur", "Maharashtra", 17.6703, 75.9011),
        Place("thane", "Thane", "Maharashtra", 19.1972, 72.9722),
        # Manipur
        Place("imphal", "Imphal", "Manipur", 24.8074, 93.9384),
        # Meghalaya
        Place("shillong", "Shillong", "Meghalaya", 25.5822, 91.8944),
        # Mizoram
        Place("aizawl", "Aizawl", "Mizoram", 23.7330, 92.7180),
        # Nagaland
        Place("dimapur", "Dimapur", "Nagaland", 25.9092, 93.7266),
        Place("kohima", "Kohima", "Nagaland", 25.6700, 94.1000),
        # Odisha
        Place("angul", "Angul", "Odisha", 20.8381, 85.0956),
        Place("bhubaneswar", "Bhubaneswar", "Odisha", 20.2700, 85.8400),
        Place("cuttack", "Cuttack", "Odisha", 20.5236, 85.7881),
        Place("rourkela", "Rourkela", "Odisha", 22.2492, 84.8828),
        Place("sambalpur", "Sambalpur", "Odisha", 21.4700, 83.9700),
        # Puducherry
        Place("puducherry", "Puducherry", "Puducherry", 11.9340, 79.8290),
        # Punjab
        Place("amritsar", "Amritsar", "Punjab", 31.6400, 74.8600),
        Place("bathinda", "Bathinda", "Punjab", 30.2300, 74.9519),
        Place("jalandhar", "Jalandhar", "Punjab", 31.3260, 75.5762),
        Place("ludhiana", "Ludhiana", "Punjab", 30.9090, 75.8516),
        Place("mandi_gobindgarh", "Mandi Gobindgarh", "Punjab", 30.4100, 76.1800),
        Place("mohali", "Mohali", "Punjab", 30.6990, 76.6930),
        Place("patiala", "Patiala", "Punjab", 30.3408, 76.4011),
        # Rajasthan
        Place("ajmer", "Ajmer", "Rajasthan", 26.4499, 74.6399),
        Place("bhiwadi", "Bhiwadi", "Rajasthan", 28.2100, 76.8700),
        Place("bikaner", "Bikaner", "Rajasthan", 28.0167, 73.3119),
        Place("jaipur", "Jaipur", "Rajasthan", 26.9150, 75.8200),
        Place("jodhpur", "Jodhpur", "Rajasthan", 26.2800, 73.0200),
        Place("kota", "Kota", "Rajasthan", 25.1800, 75.8300),
        Place("udaipur", "Udaipur", "Rajasthan", 24.5800, 73.6800),
        # Sikkim
        Place("gangtok", "Gangtok", "Sikkim", 27.3300, 88.6200),
        # Tamil Nadu
        Place("chennai", "Chennai", "Tamil Nadu", 13.0827, 80.2707),
        Place("coimbatore", "Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
        Place("erode", "Erode", "Tamil Nadu", 11.3409, 77.7171),
        Place("hosur", "Hosur", "Tamil Nadu", 12.7409, 77.8253),
        Place("madurai", "Madurai", "Tamil Nadu", 9.9252, 78.1198),
        Place("salem", "Salem", "Tamil Nadu", 11.6500, 78.1500),
        Place("thoothukudi", "Thoothukudi", "Tamil Nadu", 8.8056, 78.1450),
        Place("tiruchirappalli", "Tiruchirappalli", "Tamil Nadu", 10.7903, 78.7047),
        Place("tirunelveli", "Tirunelveli", "Tamil Nadu", 8.7136, 77.7567),
        Place("tiruppur", "Tiruppur", "Tamil Nadu", 11.1085, 77.3411),
        Place("vellore", "Vellore", "Tamil Nadu", 12.9165, 79.1325),
        # Telangana
        Place("hyderabad", "Hyderabad", "Telangana", 17.3617, 78.4747),
        Place("karimnagar", "Karimnagar", "Telangana", 18.4386, 79.1288),
        Place("nizamabad", "Nizamabad", "Telangana", 18.6720, 78.0940),
        Place("warangal", "Warangal", "Telangana", 17.9689, 79.5941),
        # Tripura
        Place("agartala", "Agartala", "Tripura", 23.8314, 91.2869),
        # Uttar Pradesh
        Place("agra", "Agra", "Uttar Pradesh", 27.1800, 78.0200),
        Place("aligarh", "Aligarh", "Uttar Pradesh", 27.8883, 78.0731),
        Place("bareilly", "Bareilly", "Uttar Pradesh", 28.3667, 79.4306),
        Place("ghaziabad", "Ghaziabad", "Uttar Pradesh", 28.6700, 77.4200),
        Place("gorakhpur", "Gorakhpur", "Uttar Pradesh", 26.7637, 83.4039),
        Place("kanpur", "Kanpur", "Uttar Pradesh", 26.4499, 80.3319),
        Place("lucknow", "Lucknow", "Uttar Pradesh", 26.8500, 80.9500),
        Place("meerut", "Meerut", "Uttar Pradesh", 28.9800, 77.7100),
        Place("moradabad", "Moradabad", "Uttar Pradesh", 28.8319, 78.7764),
        Place("muzaffarnagar", "Muzaffarnagar", "Uttar Pradesh", 29.4675, 77.7050),
        Place("noida", "Noida", "Uttar Pradesh", 28.5700, 77.3200),
        Place("prayagraj", "Prayagraj", "Uttar Pradesh", 25.4358, 81.8464),
        Place("varanasi", "Varanasi", "Uttar Pradesh", 25.3189, 83.0128),
        # Uttarakhand
        Place("dehradun", "Dehradun", "Uttarakhand", 30.3450, 78.0290),
        Place("haridwar", "Haridwar", "Uttarakhand", 29.9450, 78.1630),
        Place("rudrapur", "Rudrapur", "Uttarakhand", 28.9800, 79.4000),
        # West Bengal
        Place("asansol", "Asansol", "West Bengal", 23.6800, 86.9900),
        Place("durgapur", "Durgapur", "West Bengal", 23.5500, 87.3167),
        Place("haldia", "Haldia", "West Bengal", 22.0667, 88.0698),
        Place("howrah", "Howrah", "West Bengal", 22.5800, 88.3294),
        Place("kharagpur", "Kharagpur", "West Bengal", 22.3302, 87.3237),
        Place("kolkata", "Kolkata", "West Bengal", 22.5675, 88.3700),
        Place("siliguri", "Siliguri", "West Bengal", 26.7100, 88.4300),
    )
}


def km_from(place: Place, point: Point) -> int:
    """Straight-line distance, rounded to whole kilometres."""
    return round(distance_metres(place.point, point) / 1000)


def nearest_yard(point: Point, yards: Iterable[str]) -> tuple[Place, int]:
    """Which of the yards (PLACES codes) is closest to `point`, and how far it is in kilometres."""
    yard = min((PLACES[code] for code in yards), key=lambda y: distance_metres(y.point, point))
    return yard, km_from(yard, point)
