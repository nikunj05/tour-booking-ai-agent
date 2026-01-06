import math
from sqlalchemy import func

def paginate(query, page: int, per_page: int = 10):
    # ✅ SAFE count
    total = query.session.query(func.count()) \
        .select_from(query.subquery()) \
        .scalar()

    total_pages = math.ceil(total / per_page) if total else 1

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
