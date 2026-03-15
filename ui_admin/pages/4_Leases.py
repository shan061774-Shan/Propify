import streamlit as st
from datetime import date
import calendar
from collections import defaultdict
from ui_admin.api_client import api_delete, api_get, api_patch, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL


def add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    target_year = base_date.year + month_index // 12
    target_month = month_index % 12 + 1
    last_day = calendar.monthrange(target_year, target_month)[1]
    target_day = min(base_date.day, last_day)
    return date(target_year, target_month, target_day)

st.set_page_config(page_title="Leases | Propify", page_icon="🏢")
st.title("📄 Leases")
require_owner_login()
render_company_context()

props_r = api_get(f"{API_URL}/properties/")
units_r = api_get(f"{API_URL}/units/")
tenants_r = api_get(f"{API_URL}/tenants/")
leases_r = api_get(f"{API_URL}/leases/")

if not props_r.ok or not units_r.ok or not tenants_r.ok:
    st.error("Failed to load required data")
    st.write("properties:", props_r.status_code, props_r.text)
    st.write("units:", units_r.status_code, units_r.text)
    st.write("tenants:", tenants_r.status_code, tenants_r.text)
    st.stop()

properties = {p["id"]: p for p in props_r.json()}
units = units_r.json()
tenants = tenants_r.json()
leases = leases_r.json() if leases_r.ok else []

unit_by_id = {u["id"]: u for u in units}
tenant_by_id = {t["id"]: t for t in tenants}

st.subheader("Existing Leases")
if leases:
    # group leases by (property_name, property_address)
    grouped = defaultdict(list)
    for l in leases:
        u = unit_by_id.get(l["unit_id"])
        if not u:
            grouped[("Unknown Property", "")].append(l)
            continue
        p = properties.get(u["property_id"], {})
        key = (p.get("name", "Unknown Property"), p.get("address", ""))
        grouped[key].append(l)

    for (prop_name, prop_address), prop_leases in grouped.items():
        st.markdown(f"### 🏠 {prop_name}")
        if prop_address:
            st.write(f"📍 {prop_address}")

        # optional: show total active monthly rent for this property
        total_active_rent = 0.0
        for l in prop_leases:
            u = unit_by_id.get(l["unit_id"])
            if u and l.get("status", "active") == "active":
                total_active_rent += float(u.get("rent_amount", 0) or 0)
        st.write(f"**Active Monthly Rent:** ${total_active_rent:,.2f}")

        for l in prop_leases:
            u = unit_by_id.get(l["unit_id"])
            t = tenant_by_id.get(l["tenant_id"])
            rent_amount = float(u.get("rent_amount", 0) or 0) if u else 0.0

            lease_number = l.get("lease_number", l["id"])
            unit_number = u["unit_number"] if u else l["unit_id"]
            tenant_name = t["name"] if t else l["tenant_id"]
            lease_status = l.get("status", "active")
            lease_end = l.get("end_date") or "Open"

            with st.container(border=True):
                st.markdown(f"**Lease {lease_number}**")

                info_col1, info_col2, info_col3 = st.columns(3)
                info_col1.write(f"Unit: **#{unit_number}**")
                info_col2.write(f"Rent: **${rent_amount:,.2f}**")
                info_col3.write(f"Status: **{lease_status}**")

                st.write(f"Tenant: **{tenant_name}**")
                st.write(f"Term: **{l['start_date']} -> {lease_end}**")

                c1, c2 = st.columns(2)
                if c1.button("Deactivate", key=f"deact-{l['id']}"):
                    r = api_patch(f"{API_URL}/leases/{l['id']}", json={"status": "inactive"})
                    if r.ok:
                        st.success("Lease deactivated")
                        st.rerun()
                    else:
                        st.error(f"Deactivate failed: {r.status_code} {r.text}")

                if c2.button("Delete", key=f"del-{l['id']}"):
                    r = api_delete(f"{API_URL}/leases/{l['id']}")
                    if r.status_code in (200, 204):
                        st.success("Lease deleted")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {r.status_code} {r.text}")

        st.divider()
else:
    st.info("No leases yet.")

st.subheader("Create Lease (Property Primary)")

if not properties:
    st.warning("No properties found. Add a property first.")
    st.stop()
if not tenants:
    st.warning("No tenants found. Add tenants first.")
    st.stop()

# property-first selection
units_by_property = defaultdict(list)
for u in units:
    units_by_property[u["property_id"]].append(u)

property_options = {}
for pid, p in properties.items():
    unit_count = len(units_by_property.get(pid, []))
    label = f"{p.get('name', 'Unknown')} | {p.get('address', '')} (ID {pid}, {unit_count} units)"
    property_options[label] = pid

selected_property_label = st.selectbox("Select Property", list(property_options.keys()))
selected_property_id = property_options[selected_property_label]
selected_property = properties.get(selected_property_id, {})

available_units = sorted(
    units_by_property.get(selected_property_id, []),
    key=lambda u: str(u.get("unit_number", "")).lower(),
)

st.info(
    f"Property: {selected_property.get('name', '')} | {selected_property.get('address', '')}"
)

selected_unit = None
default_unit_rent = 0.0
if available_units:
    unit_options = {}
    for u in available_units:
        rent_amount = float(u.get("rent_amount", 0) or 0)
        unit_label = f"Apartment {u['unit_number']} (ID {u['id']}) | Rent: ${rent_amount:,.2f}"
        unit_options[unit_label] = u

    selected_unit_label = st.selectbox("Select Unit", list(unit_options.keys()))
    selected_unit = unit_options[selected_unit_label]
else:
    st.caption("No units found for this property. A default Unit 1 will be created when you create this lease.")
    default_unit_rent = st.number_input(
        "Default Unit 1 Rent",
        min_value=0.0,
        step=0.01,
        format="%.2f",
        key=f"default_unit_rent_{selected_property_id}",
    )

tenant_options = {f"{t['name']} (ID {t['id']})": t["id"] for t in tenants}
selected_tenant_label = st.selectbox("Select Tenant", list(tenant_options.keys()))
tenant_id = tenant_options[selected_tenant_label]

start_date = st.date_input("Start Date", value=date.today())
lease_term = st.selectbox("Lease Term", ["6 months", "1 year"], index=1)
term_months = 12 if lease_term == "1 year" else 6
end_date = add_months(start_date, term_months)
st.date_input("End Date (Auto)", value=end_date, disabled=True)

if st.button("Create Lease"):
    if not selected_unit:
        create_unit_payload = {
            "property_id": selected_property_id,
            "unit_number": "1",
            "description": "Single-family home",
            "rent_amount": default_unit_rent,
        }
        create_unit_response = api_post(f"{API_URL}/units/", json=create_unit_payload)
        if create_unit_response.status_code not in (200, 201):
            st.error(
                f"Failed to auto-create Unit 1: {create_unit_response.status_code} {create_unit_response.text}"
            )
            st.stop()
        selected_unit = create_unit_response.json()

    payload = {
        "unit_id": selected_unit["id"],  # still unit_id in backend
        "tenant_id": tenant_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    r = api_post(f"{API_URL}/leases/", json=payload)
    if r.status_code in (200, 201):
        st.success("Lease created")
        st.rerun()
    else:
        st.error(f"Failed to create lease: {r.status_code} {r.text}")
