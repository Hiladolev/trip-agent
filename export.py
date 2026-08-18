"""Excel export: recommendations plus a chronological trip skeleton (hotels
and flights merged into one sorted list) for offline/printable reference.
"""

from io import BytesIO

from openpyxl import Workbook


def _date_only(date_str: str) -> str:
    """Extract the date portion from a 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' string."""
    return date_str.split(" ")[0]


# Hotels only store a check-in date, no time. Assume a typical afternoon
# check-in for sort-ordering purposes only (never displayed or stored) - this
# breaks same-day ties against flight arrivals so the skeleton reads in the
# order things actually happen (e.g. arrive Koh Samui by flight, then check
# into the hotel), instead of an arbitrary insertion-order tiebreak.
ASSUMED_HOTEL_CHECKIN_TIME = "15:00"


def build_skeleton_rows(trip_data: dict) -> list[dict]:
    """Chronologically merged hotel/flight rows, shared by build_excel and
    the /preview/data endpoint."""
    rows = []
    for hotel in trip_data.get("hotels", []):
        sort_key = f"{hotel['check_in']} {ASSUMED_HOTEL_CHECKIN_TIME}"
        rows.append((sort_key, {
            "date": _date_only(hotel["check_in"]),
            "type": "Hotel",
            "location_route": hotel["city"],
            "details": f"{hotel['name']}: check-in {hotel['check_in']} -> check-out {hotel['check_out']}",
        }))
    for flight in trip_data.get("flights", []):
        sort_key = flight["departure"]  # already "YYYY-MM-DD HH:MM"
        rows.append((sort_key, {
            "date": _date_only(flight["departure"]),
            "type": "Flight",
            "location_route": f"{flight['from']} -> {flight['to']}",
            "details": f"{flight['description']}: depart {flight['departure']} -> arrive {flight['arrival']}",
        }))
    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]


def build_excel(trip_data: dict) -> BytesIO:
    wb = Workbook()

    recommendations_sheet = wb.active
    recommendations_sheet.title = "Recommendations"
    recommendations_sheet.append(
        ["City", "Place Name", "Priority", "Description", "Maps Link", "Source"]
    )
    for rec in trip_data.get("recommendations", []):
        recommendations_sheet.append([
            rec.get("city"),
            rec.get("place_name"),
            rec.get("priority"),
            rec.get("description"),
            rec.get("maps_link"),
            rec.get("source"),
        ])

    skeleton_sheet = wb.create_sheet("Trip Skeleton")
    skeleton_sheet.append(["Date", "Type", "Location/Route", "Details"])
    for row in build_skeleton_rows(trip_data):
        skeleton_sheet.append([row["date"], row["type"], row["location_route"], row["details"]])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
