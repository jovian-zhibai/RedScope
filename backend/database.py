from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_default_admin()


async def _ensure_default_admin():
    from sqlalchemy import select
    from backend.models.user import User
    import secrets
    import os

    async with async_session() as db:
        result = await db.execute(select(User).where(User.role == "admin"))
        if result.scalar_one_or_none():
            return

        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        password = secrets.token_urlsafe(16)

        admin = User(
            username="admin",
            password_hash=pwd_context.hash(password),
            display_name="系统管理员",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()

        password_file = "/app/data/init-password"
        os.makedirs(os.path.dirname(password_file), exist_ok=True)
        with open(password_file, "w") as f:
            f.write(f"RedScope 管理员初始密码\n用户名: admin\n密码: {password}\n\n请登录后立即修改密码！\n")

        from backend.core.error_handler import logger
        logger.info("="*50)
        logger.info("  默认管理员已创建")
        logger.info("  用户名: admin")
        logger.info(f"  密码已写入: {password_file}")
        logger.info("  查看: cat data/init-password")
        logger.info("="*50)
