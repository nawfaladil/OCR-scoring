import yaml
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from main_tool.core.database.db_test import get_async_session
from main_tool.core.api.users import current_active_user
from main_tool.core.database.db_test import UserConfig


router = APIRouter()

@router.get("/config")
async def get_config(
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(
        select(UserConfig).where(UserConfig.user_id == user.id)
    )
    user_config = result.scalar_one_or_none()
    if user_config is None:
        return {} # can be changed to a default config
    try:
        return yaml.safe_load(user_config.config)
    except Exception:
        raise HTTPException(status_code=500, detail="Config is not valid YAML.")

@router.post("/config")
async def update_config(
    config: dict = Body(...),
    user=Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    yaml_str = yaml.dump(config, allow_unicode=True)
    result = await session.execute(
        select(UserConfig).where(UserConfig.user_id == user.id)
    )
    user_config = result.scalar_one_or_none()
    if user_config is None:
        user_config = UserConfig(user_id=user.id, config=yaml_str)
        session.add(user_config)
    else:
        user_config.config = yaml_str
    await session.commit()
    return config
