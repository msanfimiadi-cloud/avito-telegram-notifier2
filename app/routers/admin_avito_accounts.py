from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies import get_avito_account_service, require_admin_key
from app.schemas_avito_account import AvitoAccountCreate, AvitoAccountRead, AvitoAccountUpdate, AvitoVerifyResponse
from app.services.avito_account_service import AvitoAccountConflictError, AvitoAccountNotFoundError, AvitoAccountService

router = APIRouter(prefix="/api/v1/admin/avito-accounts", tags=["admin-avito-accounts"], dependencies=[Depends(require_admin_key)])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AvitoAccountNotFoundError):
        return HTTPException(status_code=404, detail="Avito account not found")
    if isinstance(exc, AvitoAccountConflictError):
        return HTTPException(status_code=409, detail="Avito account with this profile_id or client_id already exists")
    return HTTPException(status_code=400, detail="Avito account operation failed")


@router.post("", response_model=AvitoAccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AvitoAccountCreate, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        return await service.create_account(payload)
    except (AvitoAccountConflictError, AvitoAccountNotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get("", response_model=list[AvitoAccountRead])
async def list_accounts(service: AvitoAccountService = Depends(get_avito_account_service)):
    return await service.list_accounts()


@router.get("/{account_id}", response_model=AvitoAccountRead)
async def get_account(account_id: int, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        return await service.get_account(account_id)
    except AvitoAccountNotFoundError as exc:
        raise _map_error(exc) from exc


@router.patch("/{account_id}", response_model=AvitoAccountRead)
async def update_account(account_id: int, payload: AvitoAccountUpdate, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        return await service.update_account(account_id, payload)
    except (AvitoAccountConflictError, AvitoAccountNotFoundError) as exc:
        raise _map_error(exc) from exc


@router.post("/{account_id}/verify", response_model=AvitoVerifyResponse)
async def verify_account(account_id: int, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        success, status_value, message = await service.verify_credentials(account_id)
        return AvitoVerifyResponse(success=success, status=status_value, message=message)
    except AvitoAccountNotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/{account_id}/activate", response_model=AvitoAccountRead)
async def activate_account(account_id: int, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        return await service.activate_account(account_id)
    except AvitoAccountNotFoundError as exc:
        raise _map_error(exc) from exc


@router.post("/{account_id}/deactivate", response_model=AvitoAccountRead)
async def deactivate_account(account_id: int, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        return await service.deactivate_account(account_id)
    except AvitoAccountNotFoundError as exc:
        raise _map_error(exc) from exc


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, service: AvitoAccountService = Depends(get_avito_account_service)):
    try:
        await service.delete_account(account_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AvitoAccountNotFoundError as exc:
        raise _map_error(exc) from exc
