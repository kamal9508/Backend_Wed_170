from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from .db import get_master_db, sanitize_org_name, ensure_org_collection
from .models import OrgCreate, OrgOut, AdminLogin, TokenResponse, OrgUpdate
from .auth import hash_password, verify_password, create_access_token, get_current_admin

router = APIRouter()


@router.post("/org/create", response_model=OrgOut)
async def create_org(payload: OrgCreate):
    db = get_master_db()
    name = payload.organization_name.strip()
    existing = await db.organizations.find_one({"organization_name": name})
    if existing:
        raise HTTPException(
            status_code=400, detail="Organization already exists")

    coll_name = sanitize_org_name(name)
    # ensure collection exists
    await ensure_org_collection(db, coll_name)

    org_doc = {
        "organization_name": name,
        "collection_name": coll_name,
        "created_at": datetime.utcnow(),
    }
    org_res = await db.organizations.insert_one(org_doc)

    # create admin
    hashed = hash_password(payload.password)
    admin_doc = {"email": payload.email,
                 "password": hashed, "org_id": org_res.inserted_id}
    admin_res = await db.admins.insert_one(admin_doc)

    # update org with admin reference
    await db.organizations.update_one({"_id": org_res.inserted_id}, {"$set": {"admin_id": admin_res.inserted_id}})

    return OrgOut(
        id=str(org_res.inserted_id),
        organization_name=name,
        collection_name=coll_name,
        admin_email=payload.email,
    )


@router.get("/org/get")
async def get_org(organization_name: str):
    db = get_master_db()
    org = await db.organizations.find_one({"organization_name": organization_name})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org["id"] = str(org.get("_id"))
    # convert ObjectId fields to strings for admin/org ids
    if "admin_id" in org:
        org["admin_id"] = str(org["admin_id"])
    if "org_id" in org:
        org["org_id"] = str(org["org_id"])
    org.pop("_id", None)
    return org


@router.put("/org/update")
async def update_org(data: OrgUpdate, admin=Depends(get_current_admin)):
    db = get_master_db()
    org_id = admin.get("org_id")
    # org_id may be ObjectId or string - make sure ObjectId
    try:
        org_obj_id = ObjectId(org_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid org id in token")

    org = await db.organizations.find_one({"_id": org_obj_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # handle rename
    if data.organization_name:
        new_name = data.organization_name.strip()
        if new_name != org["organization_name"]:
            exists = await db.organizations.find_one({"organization_name": new_name})
            if exists:
                raise HTTPException(
                    status_code=400, detail="New organization name already exists")

            old_coll = org["collection_name"]
            new_coll = sanitize_org_name(new_name)
            await ensure_org_collection(db, new_coll)

            # copy documents from old to new (drop _id to avoid conflicts)
            old = db[old_coll]
            new = db[new_coll]
            docs = []
            async for d in old.find():
                d.pop("_id", None)
                docs.append(d)
            if docs:
                await new.insert_many(docs)
            # drop old collection
            await old.drop()

            # update org metadata
            await db.organizations.update_one({"_id": org_obj_id}, {"$set": {"organization_name": new_name, "collection_name": new_coll}})

    # update admin email/password if provided
    update_admin = {}
    if data.email:
        update_admin["email"] = data.email
    if data.password:
        update_admin["password"] = hash_password(data.password)
    if update_admin:
        await db.admins.update_one({"_id": admin.get("_id")}, {"$set": update_admin})

    return {"status": "ok"}


@router.delete("/org/delete")
async def delete_org(organization_name: str, admin=Depends(get_current_admin)):
    db = get_master_db()
    org = await db.organizations.find_one({"organization_name": organization_name})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # verify admin belongs to this org
    admin_org = admin.get("org_id")
    if str(admin_org) != str(org.get("_id")):
        raise HTTPException(
            status_code=403, detail="Forbidden: not authorized to delete this organization")

    coll = org.get("collection_name")
    if coll:
        try:
            await db[coll].drop()
        except Exception:
            pass

    # remove admin and org entries
    await db.admins.delete_many({"org_id": org.get("_id")})
    await db.organizations.delete_one({"_id": org.get("_id")})

    return {"status": "deleted"}


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(payload: AdminLogin):
    db = get_master_db()
    admin = await db.admins.find_one({"email": payload.email})
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, admin.get("password")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        {"admin_id": str(admin.get("_id")), "org_id": str(admin.get("org_id"))})
    return TokenResponse(access_token=token)


@router.get("/health")
async def health_check():
    """Health check endpoint to verify Mongo connectivity and return diagnostics."""
    db = get_master_db()
    try:
        # Motor returns a coroutine for command
        pong = await db.command({"ping": 1})
        return {"status": "ok", "mongo": pong}
    except Exception as e:
        return {"status": "error", "mongo_error": str(e)}
