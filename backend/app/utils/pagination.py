import math

def paginate(query, page: int, per_page: int = 10):
    total = query.count()
    total_pages = math.ceil(total / per_page)

    items = (
        query
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages
    }
