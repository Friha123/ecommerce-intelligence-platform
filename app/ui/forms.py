"""Formulaire de saisie d'une commande, partagé par les pages « Modèle 1 » et « Modèle 2 »."""
from __future__ import annotations

from datetime import date, datetime, time

import streamlit as st


def order_form(options: dict, key: str, submit_label: str, ask_promise: bool) -> tuple[bool, dict]:
    states = [s["code"] for s in options["states"]]
    names = {s["code"]: f"{s['code']} · {s['name']}" for s in options["states"]}
    categories = options["categories"] or ["other"]
    payments = options["payment_types"] or ["credit_card"]
    with st.form(key):
        c1, c2, c3 = st.columns(3)
        customer_state = c1.selectbox("État du client", states, index=0, format_func=names.get)
        seller_state = c2.selectbox("État du vendeur", states, index=states.index("SP") if "SP" in states else 0, format_func=names.get)
        category = c3.selectbox("Catégorie du produit", categories)
        price = c1.number_input("Prix des articles (R$)", 1.0, 20000.0, 120.0, step=10.0)
        freight = c2.number_input("Frais de port (R$)", 0.0, 2000.0, 25.0, step=1.0)
        weight_kg = c3.number_input("Poids total (kg)", 0.05, 100.0, 1.5, step=0.1)
        volume_l = c1.number_input("Volume total (litres)", 0.1, 500.0, 8.0, step=0.5)
        nb_items = c2.number_input("Nombre d'articles", 1, 20, 1)
        payment = c3.selectbox("Mode de paiement", payments)
        d = c1.date_input("Date d'achat", value=date.today())
        t = c2.time_input("Heure d'achat", value=time(14, 0))
        promised = c3.number_input("Promesse actuelle d'Olist (jours)", 1, 120, 24) if ask_promise else None
        submitted = st.form_submit_button(submit_label, type="primary", width="stretch")
    inputs = {"customer_state": customer_state, "seller_state": seller_state, "categorie_grouped": category, "payment_type": payment,
              "total_price": price, "total_freight": freight, "total_weight_g": weight_kg * 1000.0, "total_volume_cm3": volume_l * 1000.0,
              "nb_items": int(nb_items), "purchase_datetime": datetime.combine(d, t), "promised_days": float(promised) if promised else None}
    return submitted, inputs
