import streamlit as st
from collections import defaultdict
from ui_admin.api_client import api_delete, api_get, api_patch, api_post
from ui_admin.auth_guard import render_company_context, require_owner_login
from ui_admin.config import API_URL

st.set_page_config(page_title="Properties | Propify", page_icon="🏢", layout="wide")
st.title("🏠 Properties")
require_owner_login()
render_company_context()

props_r = api_get(f"{API_URL}/properties/")
units_r = api_get(f"{API_URL}/units/")

if not props_r.ok:
    st.error("Failed to load properties")
    st.write("status:", props_r.status_code)
    st.write("body:", props_r.text)
    st.stop()

properties = props_r.json()
units = units_r.json() if units_r.ok else []

# group units by property_id
units_by_prop_id = defaultdict(list)
for u in units:
    units_by_prop_id[u["property_id"]].append(u)

# group properties by name
prop_groups = defaultdict(list)
for p in properties:
    prop_groups[p["name"].strip()].append(p)

properties_by_name = defaultdict(list)
for p in properties:
    properties_by_name[p["name"].strip().lower()].append(p)


GROUP_ACCENT_COLORS = [
    "#0f766e",
    "#1d4ed8",
    "#b45309",
    "#0f766e",
    "#7c2d12",
    "#7e22ce",
]


def _group_color(group_name: str) -> str:
    return GROUP_ACCENT_COLORS[abs(hash(group_name.lower())) % len(GROUP_ACCENT_COLORS)]


def _render_group_title(name: str, location_count: int, total_group_units: int, color: str) -> None:
    st.markdown(
        (
            f"<div style='border-left:8px solid {color};padding:10px 12px;"
            "border-radius:8px;background:#f8fafc;margin-bottom:8px;'>"
            f"<div style='font-size:1.25rem;font-weight:700;color:{color};'>{name}</div>"
            f"<div style='font-size:0.9rem;color:#334155;'>"
            f"{location_count} location{'s' if location_count != 1 else ''} · {total_group_units} unit{'s' if total_group_units != 1 else ''}"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_location_title(address: str, property_id: int, color: str) -> None:
    st.markdown(
        (
            f"<div style='border:1px solid {color}33;padding:8px 10px;border-radius:8px;background:#ffffff;'>"
            f"<div style='font-weight:700;color:#0f172a;'>{address}</div>"
            f"<div style='font-size:0.8rem;color:#475569;'>Property ID {property_id}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def sync_address_from_name():
    typed_name = st.session_state.get("property_name_input", "").strip().lower()
    matches = properties_by_name.get(typed_name, [])

    if len(matches) == 1:
        matched_property = matches[0]
        current_address = st.session_state.get("property_address_input", "").strip()
        address_was_autofilled = st.session_state.get("property_address_autofilled", False)

        if not current_address or address_was_autofilled:
            st.session_state["property_address_input"] = matched_property["address"].strip()
            st.session_state["property_address_autofilled"] = True
            st.session_state["matched_property_id"] = matched_property["id"]
    else:
        st.session_state["matched_property_id"] = None
        st.session_state["property_address_autofilled"] = False


def mark_address_as_manual():
    st.session_state["property_address_autofilled"] = False


def reset_property_form_state():
    st.session_state["property_name_input"] = ""
    st.session_state["property_address_input"] = ""
    st.session_state["property_unit_number_input"] = "1"
    st.session_state["property_rent_amount_input"] = 0.0
    st.session_state["property_grace_days_input"] = 3
    st.session_state["property_late_fee_input"] = 30
    st.session_state["property_address_autofilled"] = False
    st.session_state["matched_property_id"] = None
    st.session_state["clear_property_form"] = False

total_properties = len(properties)
total_units = len(units)
total_rent = sum(float(u["rent_amount"]) for u in units)

st.subheader("Existing Properties")
st.caption("Grouped by property name, then split into address sections with unit cards under each location.")

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Properties", total_properties)
metric_col2.metric("Units", total_units)
metric_col3.metric("Total Rent", f"${total_rent:,.2f}")

if not properties:
    st.info("No properties yet.")
else:
    sorted_groups = sorted(prop_groups.items(), key=lambda item: item[0].lower())

    for name, grouped_properties in sorted_groups:
        grouped_properties = sorted(grouped_properties, key=lambda prop: prop["address"].strip().lower())
        total_group_units = sum(len(units_by_prop_id[prop["id"]]) for prop in grouped_properties)
        location_count = len(grouped_properties)
        accent_color = _group_color(name)

        with st.container(border=True):
            _render_group_title(name, location_count, total_group_units, accent_color)

            for index, prop in enumerate(grouped_properties):
                if index > 0:
                    st.divider()

                with st.container(border=True):
                    header_col, action_col = st.columns([5, 1.2])
                    with header_col:
                        _render_location_title(prop["address"], prop["id"], accent_color)
                        st.caption(
                            f"Late fee: ${float(prop.get('late_fee_amount', 30) or 30):,.2f} after day {int(prop.get('grace_period_days', 3) or 3)} of the month."
                        )
                    with action_col:
                        st.caption("Location Action")
                        if st.button("Delete", key=f"delete-property-{prop['id']}", use_container_width=True):
                            delete_response = api_delete(f"{API_URL}/properties/{prop['id']}")
                            if delete_response.status_code in (200, 204):
                                st.success(f"Deleted property at {prop['address']}")
                                st.rerun()
                            else:
                                st.error(
                                    f"Delete failed: {delete_response.status_code} {delete_response.text}"
                                )

                with st.expander(f"Edit Location (Property ID {prop['id']})"):
                    with st.form(f"edit-property-form-{prop['id']}"):
                        edit_name = st.text_input("Property Name", value=prop["name"], key=f"edit-prop-name-{prop['id']}")
                        edit_address = st.text_input(
                            "Property Address",
                            value=prop["address"],
                            key=f"edit-prop-address-{prop['id']}",
                        )
                        edit_col1, edit_col2 = st.columns(2)
                        edit_grace_days = edit_col1.number_input(
                            "Grace Period Days",
                            min_value=0,
                            step=1,
                            value=int(prop.get("grace_period_days", 3) or 3),
                            key=f"edit-prop-grace-{prop['id']}",
                        )
                        edit_late_fee = edit_col2.number_input(
                            "Late Fee Amount",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=float(prop.get("late_fee_amount", 30) or 30),
                            key=f"edit-prop-late-fee-{prop['id']}",
                        )
                        save_property = st.form_submit_button("Save Property Changes")

                    if save_property:
                        payload = {
                            "name": edit_name.strip(),
                            "address": edit_address.strip(),
                            "grace_period_days": int(edit_grace_days),
                            "late_fee_amount": int(edit_late_fee),
                        }
                        update_response = api_patch(f"{API_URL}/properties/{prop['id']}", json=payload)
                        if update_response.status_code in (200, 201):
                            st.success("Property updated")
                            st.rerun()
                        else:
                            st.error(
                                f"Property update failed: {update_response.status_code} {update_response.text}"
                            )

                property_units = sorted(
                    units_by_prop_id[prop["id"]],
                    key=lambda unit: str(unit["unit_number"]).lower(),
                )

                unit_count = len(property_units)
                st.caption(
                    f"Deleting this location removes {unit_count} unit{'s' if unit_count != 1 else ''} and related leases, payments, and maintenance records."
                )

                if not property_units:
                    st.info("No units added yet for this location.")
                    add_unit_col1, add_unit_col2, add_unit_col3 = st.columns([1, 2, 1])
                    empty_unit_key = f"empty-prop-unit-number-{prop['id']}"
                    if empty_unit_key not in st.session_state:
                        st.session_state[empty_unit_key] = "1"

                    empty_unit_number = add_unit_col1.text_input(
                        "Unit Number",
                        key=empty_unit_key,
                    )
                    empty_unit_rent = add_unit_col3.number_input(
                        "Rent",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=f"empty-prop-unit-rent-{prop['id']}",
                    )

                    if st.button("Add Unit", key=f"empty-prop-add-unit-{prop['id']}"):
                        unit_number_to_create = empty_unit_number.strip() or "1"
                        create_unit_response = api_post(
                            f"{API_URL}/units/",
                            json={
                                "property_id": prop["id"],
                                "unit_number": unit_number_to_create,
                                "description": "",
                                "rent_amount": empty_unit_rent,
                            },
                        )
                        if create_unit_response.status_code in (200, 201):
                            st.success("Unit added")
                            st.rerun()
                        else:
                            st.error(
                                f"Failed to add unit: {create_unit_response.status_code} {create_unit_response.text}"
                            )
                    continue

                unit_columns = st.columns(min(3, max(1, len(property_units))))
                for idx, unit in enumerate(property_units):
                    with unit_columns[idx % len(unit_columns)]:
                        with st.container(border=True):
                            st.markdown(
                                (
                                    f"<div style='border-left:4px solid {accent_color};padding-left:8px;margin-bottom:6px;'>"
                                    f"<span style='font-weight:700;'>Unit {unit['unit_number']}</span>"
                                    f" <span style='color:#64748b;font-size:0.85rem;'>(ID {unit['id']})</span>"
                                    "</div>"
                                ),
                                unsafe_allow_html=True,
                            )
                            unit_header_col, unit_action_col = st.columns([3, 1])
                            with unit_header_col:
                                st.caption("Unit Details")
                            with unit_action_col:
                                if st.button("Delete", key=f"delete-unit-{unit['id']}"):
                                    delete_unit_response = api_delete(f"{API_URL}/units/{unit['id']}")
                                    if delete_unit_response.status_code in (200, 204):
                                        st.success(f"Deleted unit {unit['unit_number']}")
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Unit delete failed: {delete_unit_response.status_code} {delete_unit_response.text}"
                                        )
                            if unit.get("description"):
                                st.write(unit["description"])
                            else:
                                st.write("No description")
                            st.markdown(f"**${float(unit['rent_amount']):,.2f}**")

                            with st.expander("Edit Unit"):
                                with st.form(f"edit-unit-form-{unit['id']}"):
                                    edit_unit_number = st.text_input(
                                        "Unit Number",
                                        value=str(unit["unit_number"]),
                                        key=f"edit-unit-number-{unit['id']}",
                                    )
                                    edit_unit_rent = st.number_input(
                                        "Rent Amount",
                                        min_value=0.0,
                                        step=0.01,
                                        format="%.2f",
                                        value=float(unit.get("rent_amount", 0) or 0),
                                        key=f"edit-unit-rent-{unit['id']}",
                                    )
                                    save_unit = st.form_submit_button("Save Unit Changes")

                                if save_unit:
                                    payload = {
                                        "unit_number": edit_unit_number.strip(),
                                        "rent_amount": edit_unit_rent,
                                    }
                                    update_unit_response = api_patch(
                                        f"{API_URL}/units/{unit['id']}",
                                        json=payload,
                                    )
                                    if update_unit_response.status_code in (200, 201):
                                        st.success(f"Updated unit {edit_unit_number.strip()}")
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Unit update failed: {update_unit_response.status_code} {update_unit_response.text}"
                                        )

            st.write("")

st.subheader("Add Property or Unit")
st.caption("If the property already exists, entering a new unit number will add that unit to the existing location.")

st.session_state.setdefault("property_name_input", "")
st.session_state.setdefault("property_address_input", "")
st.session_state.setdefault("property_unit_number_input", "1")
st.session_state.setdefault("property_rent_amount_input", 0.0)
st.session_state.setdefault("property_grace_days_input", 3)
st.session_state.setdefault("property_late_fee_input", 30)
st.session_state.setdefault("property_address_autofilled", False)
st.session_state.setdefault("matched_property_id", None)
st.session_state.setdefault("clear_property_form", False)

if st.session_state.get("clear_property_form"):
    reset_property_form_state()

form_col1, form_col2 = st.columns(2)
name = form_col1.text_input(
    "Name",
    key="property_name_input",
    on_change=sync_address_from_name,
)
address = form_col2.text_input(
    "Address",
    key="property_address_input",
    on_change=mark_address_as_manual,
)

matched_properties = properties_by_name.get(name.strip().lower(), []) if name.strip() else []
if len(matched_properties) == 1:
    matched_property = matched_properties[0]
    existing_units = sorted(
        units_by_prop_id.get(matched_property["id"], []),
        key=lambda unit: str(unit["unit_number"]).lower(),
    )
    existing_unit_labels = ", ".join(str(unit["unit_number"]) for unit in existing_units) or "none"
    st.info(
        f"Matched existing property: {matched_property['address']} | Existing units: {existing_unit_labels}"
    )
elif len(matched_properties) > 1:
    matching_addresses = ", ".join(sorted(p["address"] for p in matched_properties))
    st.warning(f"Multiple locations match this name. Confirm the address: {matching_addresses}")

unit_col1, unit_col2 = st.columns([1, 1])
unit_number = unit_col1.text_input("Initial Unit Number (optional)", key="property_unit_number_input")
rent_amount = unit_col2.number_input(
    "Initial Unit Rent",
    min_value=0.0,
    step=0.01,
    format="%.2f",
    key="property_rent_amount_input",
)
settings_col1, settings_col2 = st.columns(2)
grace_period_days = settings_col1.number_input(
    "Grace Period Days",
    min_value=0,
    step=1,
    key="property_grace_days_input",
)
late_fee_amount = settings_col2.number_input(
    "Late Fee Amount",
    min_value=0.0,
    step=1.0,
    format="%.2f",
    key="property_late_fee_input",
)
submitted = st.button("Add Property", key="add_property_submit")

if submitted:
    if not name.strip() or not address.strip():
        st.warning("Name and Address are required")
        st.stop()

    normalized_name = name.strip()
    normalized_address = address.strip()
    existing_property = next(
        (
            p for p in properties
            if p["name"].strip().lower() == normalized_name.lower()
            and p["address"].strip().lower() == normalized_address.lower()
        ),
        None,
    )

    target_property = existing_property
    property_created = False

    if existing_property and not unit_number.strip():
        st.warning("Property already exists. Enter a unit number to add another unit to this location.")
        st.stop()

    if not existing_property:
        create_prop = api_post(
            f"{API_URL}/properties/",
            json={
                "name": normalized_name,
                "address": normalized_address,
                "grace_period_days": int(grace_period_days),
                "late_fee_amount": int(late_fee_amount),
            },
        )

        if create_prop.status_code not in (200, 201):
            st.error(f"Failed to add property: {create_prop.status_code} {create_prop.text}")
            st.stop()

        target_property = create_prop.json()
        property_created = True
        st.success("Property added")

    if unit_number.strip():
        existing_units = units_by_prop_id.get(target_property["id"], [])
        duplicate_unit = any(
            str(unit["unit_number"]).strip().lower() == unit_number.strip().lower()
            for unit in existing_units
        )
        if duplicate_unit:
            st.warning("That unit number already exists for this property.")
            st.stop()

        create_unit = api_post(
            f"{API_URL}/units/",
            json={
                "property_id": target_property["id"],
                "unit_number": unit_number.strip(),
                "description": "",
                "rent_amount": rent_amount,
            },
        )
        if create_unit.status_code in (200, 201):
            if property_created:
                st.success("Initial unit added")
            else:
                st.success("Unit added to existing property")
        else:
            if property_created:
                st.error(f"Property added, but unit failed: {create_unit.status_code} {create_unit.text}")
            else:
                st.error(f"Failed to add unit: {create_unit.status_code} {create_unit.text}")

    st.session_state["clear_property_form"] = True

    st.rerun()
