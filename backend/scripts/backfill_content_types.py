import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.legal_classifier import classify_content_type

async def run_backfill():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('SELECT id, title, excerpt, full_text, source, url FROM judgments'))
        rows = result.fetchall()
        print(f'Found {len(rows)} judgments in DB.')
        updated_count = 0
        for r in rows:
            jid, title, excerpt, full_text, source, url = r[0], r[1] or '', r[2] or '', r[3] or '', r[4] or '', r[5] or ''
            ctype, cconf = classify_content_type(title=title, text=full_text or excerpt, source=source, url=url)
            await session.execute(
                text('UPDATE judgments SET content_type = :ctype, content_type_confidence = :cconf WHERE id = :id'),
                {'ctype': ctype, 'cconf': float(cconf), 'id': jid}
            )
            updated_count += 1
        await session.commit()
        print(f'Successfully updated {updated_count} judgments to proper content_type!')

if __name__ == '__main__':
    asyncio.run(run_backfill())
