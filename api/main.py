import os
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from rental_core.auth import get_current_owner, require_role
from rental_core.db import Base, engine

os.makedirs("uploads/maintenance", exist_ok=True)
os.makedirs("ui_admin/static", exist_ok=True)

# register all models
from rental_core.models import (  # noqa
    contractor,
    document,
    lease,
    maintenance,
    owner,
    owner_admin,
    owner_password_reset,
    owner_contractor_link,
    owner_tenant_link,
    payment,
    property,
    tenant,
    unit,
    utility_charge,
)

# register all routers
from rental_core.routers import (
    tenants,
    properties,
    units,
    leases,
    payments,
    maintenance as maintenance_router,
    documents,
    utility_charges,
    contractors,
    network,
    automation,
    owner as owner_router,
    portal as portal_router,
)

app = FastAPI()

admin_dependencies = [Depends(get_current_owner), Depends(require_role("owner", "manager"))]

app.include_router(properties.router, dependencies=admin_dependencies)
app.include_router(units.router, dependencies=admin_dependencies)
app.include_router(tenants.router, dependencies=admin_dependencies)
app.include_router(leases.router, dependencies=admin_dependencies)
app.include_router(payments.router, dependencies=admin_dependencies)
app.include_router(maintenance_router.router, dependencies=admin_dependencies)
app.include_router(documents.router, dependencies=admin_dependencies)
app.include_router(utility_charges.router, dependencies=admin_dependencies)
app.include_router(contractors.router, dependencies=admin_dependencies)
app.include_router(network.router, dependencies=admin_dependencies)
app.include_router(automation.router, dependencies=admin_dependencies)
app.include_router(owner_router.router)
app.include_router(portal_router.router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="ui_admin/static"), name="static")