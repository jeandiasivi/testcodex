
import json
from typing import List, Optional

import gspread
import pandas as pd
import streamlit as st
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from google.oauth2.service_account import Credentials

SPREADSHEET_NAME = "Suivi et Affection PC"
WORKSHEET_NAME = "Affectations"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client_from_service_account(uploaded_file) -> gspread.Client:
    creds_dict = json.load(uploaded_file)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


def get_worksheet(client: gspread.Client):
    spreadsheet = client.open(SPREADSHEET_NAME)
    return spreadsheet.worksheet(WORKSHEET_NAME)


def read_data(ws) -> pd.DataFrame:
    records = ws.get_all_records()
    if not records:
        headers = ws.row_values(1)
        if headers:
            return pd.DataFrame(columns=headers)
        return pd.DataFrame()
    return pd.DataFrame(records)


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.astype("string").fillna("")


def find_matricule_column(columns: List[str]) -> Optional[str]:
    for col in columns:
        if "matricule" in col.lower():
            return col
    return None


def append_row(ws, values: List[str]) -> None:
    ws.append_row(values, value_input_option="USER_ENTERED")


def update_row_by_matricule(ws, headers: List[str], matricule_col: str, matricule_value: str, values: List[str]) -> bool:
    all_values = ws.get_all_values()
    col_idx = headers.index(matricule_col)
    for i, row in enumerate(all_values[1:], start=2):
        current = row[col_idx] if col_idx < len(row) else ""
        if str(current).strip() == str(matricule_value).strip():
            ws.update(f"A{i}", [values], value_input_option="USER_ENTERED")
            return True
    return False


def delete_row_by_matricule(ws, headers: List[str], matricule_col: str, matricule_value: str) -> bool:
    all_values = ws.get_all_values()
    col_idx = headers.index(matricule_col)
    for i, row in enumerate(all_values[1:], start=2):
        current = row[col_idx] if col_idx < len(row) else ""
        if str(current).strip() == str(matricule_value).strip():
            ws.delete_rows(i)
            return True
    return False


def show_dashboard(df: pd.DataFrame, headers: List[str]) -> None:
    st.subheader("📊 Tableau de bord")
    if df.empty:
        st.info("Aucune donnée à analyser.")
        return

    total_rows = len(df)
    matricule_col = find_matricule_column(headers)
    unique_matricules = df[matricule_col].nunique() if matricule_col and matricule_col in df.columns else 0

    col_asset = next((c for c in headers if "inventaire" in c.lower() or "pc" in c.lower()), None)
    assigned_assets = 0
    if col_asset and col_asset in df.columns:
        assigned_assets = df[col_asset].astype(str).str.strip().ne("").sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total lignes", total_rows)
    c2.metric("Matricules uniques", unique_matricules)
    c3.metric("PC inventoriés (non vides)", int(assigned_assets))



def show_search_and_read(df_display: pd.DataFrame, headers: List[str]) -> pd.DataFrame:
    st.subheader("🔎 Recherche & lecture")
    search_text = st.text_input("Rechercher un texte dans toutes les colonnes")
    selected_col = st.selectbox("Filtrer par colonne", ["(aucun)"] + headers)
    filter_value = st.text_input("Valeur du filtre (contient)") if selected_col != "(aucun)" else ""

    filtered_df = df_display.copy()
    if search_text:
        mask = filtered_df.apply(lambda row: row.astype(str).str.contains(search_text, case=False, na=False).any(), axis=1)
        filtered_df = filtered_df[mask]
    if selected_col != "(aucun)" and filter_value:
        filtered_df = filtered_df[filtered_df[selected_col].astype(str).str.contains(filter_value, case=False, na=False)]

    st.dataframe(filtered_df, width="stretch")
    return filtered_df


def show_add_form(ws, headers: List[str]) -> None:
    st.subheader("➕ Ajouter")
    with st.form("add_form"):
        add_values = [st.text_input(f"{h}", key=f"add_{h}") for h in headers]
        add_btn = st.form_submit_button("Ajouter")
        if add_btn:
            try:
                append_row(ws, add_values)
                st.success("Ligne ajoutée avec succès.")
                st.rerun()
            except APIError as exc:
                st.error(f"Erreur Google lors de l'ajout : {exc}")


def show_update_form(ws, headers: List[str], matricule_col: Optional[str]) -> None:
    st.subheader("✏️ Modifier")
    if not matricule_col:
        st.warning("Aucune colonne matricule détectée.")
        return

    with st.form("update_form"):
        matricule_to_update = st.text_input("Numéro matricule à modifier", key="update_matricule")
        update_values = [st.text_input(f"Nouveau {h}", key=f"upd_{h}") for h in headers]
        update_btn = st.form_submit_button("Modifier")
        if update_btn:
            if not matricule_to_update.strip():
                st.error("Veuillez saisir un numéro matricule.")
            else:
                try:
                    ok = update_row_by_matricule(ws, headers, matricule_col, matricule_to_update, update_values)
                    if ok:
                        st.success("Ligne modifiée avec succès.")
                        st.rerun()
                    else:
                        st.warning("Aucune ligne trouvée pour ce numéro matricule.")
                except APIError as exc:
                    st.error(f"Erreur Google lors de la modification : {exc}")


def show_delete_form(ws, headers: List[str], matricule_col: Optional[str]) -> None:
    st.subheader("🗑️ Supprimer")
    if not matricule_col:
        st.warning("Aucune colonne matricule détectée.")
        return

    with st.form("delete_form"):
        matricule_to_delete = st.text_input("Numéro matricule à supprimer", key="delete_matricule")
        confirm_delete = st.checkbox("Je confirme la suppression")
        delete_btn = st.form_submit_button("Supprimer")
        if delete_btn:
            if not confirm_delete:
                st.error("Veuillez cocher la confirmation avant suppression.")
            elif not matricule_to_delete.strip():
                st.error("Veuillez saisir un numéro matricule.")
            else:
                try:
                    ok = delete_row_by_matricule(ws, headers, matricule_col, matricule_to_delete)
                    if ok:
                        st.success("Ligne supprimée avec succès.")
                        st.rerun()
                    else:
                        st.warning("Aucune ligne trouvée pour ce numéro matricule.")
                except APIError as exc:
                    st.error(f"Erreur Google lors de la suppression : {exc}")


def main() -> None:
    st.set_page_config(page_title="Suivi & Affectation PC", layout="wide")
    st.title("Application de gestion Suivi et Affection PC")
    st.caption("Feuille cible : 'Suivi et Affection PC' → onglet 'Affectations'.")

    st.sidebar.header("Connexion Google")
    uploaded_file = st.sidebar.file_uploader("Importer le fichier JSON du compte de service", type=["json"])
    st.sidebar.markdown("---")
    menu = st.sidebar.radio(
        "Menu",
        ["Recherche", "Lire", "Modifier", "Supprimer"],
    )

    if not uploaded_file:
        st.info("Ajoutez votre fichier JSON de compte de service dans la barre latérale pour démarrer.")
        return

    try:
        client = get_client_from_service_account(uploaded_file)
        worksheet = get_worksheet(client)
        df = read_data(worksheet)
    except SpreadsheetNotFound:
        st.error("Le fichier Google Sheets 'Suivi et Affection PC' est introuvable ou non partagé.")
        st.stop()
    except WorksheetNotFound:
        st.error("L'onglet 'Affectations' est introuvable.")
        st.stop()
    except APIError as exc:
        st.error(f"Erreur API Google Sheets : {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Connexion impossible : {exc}")
        st.stop()

    headers = worksheet.row_values(1)
    if not headers:
        st.error("Aucun en-tête trouvé en ligne 1.")
        return

    df_display = prepare_display_df(df)
    matricule_col = find_matricule_column(headers)

    show_dashboard(df_display, headers)
    st.markdown("---")

    if menu == "Recherche":
        show_search_and_read(df_display, headers)
    elif menu == "Lire":
        st.subheader("📄 Lire toutes les données")
        st.dataframe(df_display, width="stretch")
    elif menu == "Modifier":
        show_update_form(worksheet, headers, matricule_col)
    elif menu == "Supprimer":
        show_delete_form(worksheet, headers, matricule_col)

    st.markdown("---")
    show_add_form(worksheet, headers)


if __name__ == "__main__":
    main()
