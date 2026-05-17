import asyncio
from auth.service import AuthService
from data_access.database import AsyncSessionLocal
from data_access.models.user import UserRole

async def main():
    async with AsyncSessionLocal() as s:
        svc = AuthService(s)
        await svc.create_user("admin@caern.local", "admin", "caern2024!", UserRole.admin)
        await s.commit()
        print("Admin olusturuldu: admin@caern.local / caern2024!")

asyncio.run(main())
