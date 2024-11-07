import streamlit as st
import pandas as pd
import re
from openpyxl.styles import Alignment
from io import BytesIO

# Your existing functions
def parse_pje(pje_text):
    matches = re.findall(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}).*?<b>Autuação:</b>(\d{2}/\d{2}/\d{4})", str(pje_text))
    parsed_data = {}
    if not matches:
        parsed_data["Processo 1"] = "não informado"
        parsed_data["Autuação 1"] = "não informado"
    else:
        for i, (processo, autuacao) in enumerate(matches, start=1):
            parsed_data[f"Processo {i}"] = processo.strip()
            parsed_data[f"Autuação {i}"] = autuacao.strip()
    return pd.Series(parsed_data)

def parse_partes(partes_text):
    if pd.isna(partes_text) or partes_text == "":
        return pd.Series()
    clean_text = re.sub(r"</br>\s*<b>", "<b>", partes_text)
    matches = re.findall(r"<b>([^<]+?)\s*:\s*</b>\s*([^<]+)", clean_text)
    parsed_elements = {}
    seen_elements = {}
    for element_name, element_value in matches:
        element_name = element_name.strip()
        element_value = element_value.strip()
        birthdate_match = re.search(r"\(NASCIMENTO:\s*(\d{2}/\d{2}/\d{4})\)", element_value)
        if birthdate_match:
            name = re.sub(r"\s*\(NASCIMENTO:.*?\)", "", element_value).strip().upper()
            birthdate = birthdate_match.group(1)
            if element_name not in seen_elements:
                seen_elements[element_name] = set()
            if (name, birthdate) not in seen_elements[element_name]:
                seen_elements[element_name].add((name, birthdate))
                name_count = len([key for key in parsed_elements.keys() if "CRIANÇA OU ADOLESCENTE" in key]) + 1
                parsed_elements[f"CRIANÇA OU ADOLESCENTE {name_count}"] = name
                parsed_elements[f"NASCIMENTO {name_count}"] = birthdate
        else:
            if element_name not in seen_elements:
                seen_elements[element_name] = set()
            if element_value not in seen_elements[element_name]:
                seen_elements[element_name].add(element_value)
                count = len([key for key in parsed_elements.keys() if element_name in key]) + 1
                element_name_with_suffix = f"{element_name} {count}"
                parsed_elements[element_name_with_suffix] = element_value.strip().upper()
    return pd.Series(parsed_elements)

# Streamlit app layout
st.title("Aplicativo para limpeza dos dados")
st.write("Faça o upload de um arquivo de Excel para processar os dados.")

# File upload widget
uploaded_file = st.file_uploader("Escolha um arquivo de Excel", type="xlsx")

if uploaded_file:
    data = pd.read_excel(uploaded_file)

    # Parse data using your functions
    parsed_pje = data['PJE'].apply(parse_pje)
    parsed_partes = data['PARTES'].apply(parse_partes)

    # Combine parsed data
    final_data = pd.concat([data.drop(columns=['PJE', 'PARTES']), parsed_pje, parsed_partes], axis=1)

    # Reorder columns
    original_columns = [col for col in data.columns if col not in ['PJE', 'PARTES']]
    processo_autuacao_cols = [col for col in final_data.columns if col.startswith('Processo') or col.startswith('Autuação')]
    instituicao_col = [col for col in final_data.columns if 'INSTITUIÇÃO' in col]
    requerente_cols = [col for col in final_data.columns if 'REQUERENTE' in col]
    requerido_cols = [col for col in final_data.columns if 'REQUERIDO' in col]
    crianca_cols = [col for col in final_data.columns if 'CRIANÇA OU ADOLESCENTE' in col]
    nascimento_cols = [col for col in final_data.columns if 'NASCIMENTO' in col]

    # Combine column order to keep pairs adjacent
    final_column_order = (
        original_columns +
        processo_autuacao_cols +
        instituicao_col +
        requerente_cols +
        requerido_cols +
        [item for pair in zip(crianca_cols, nascimento_cols) for item in pair]  # Interleave CRIANÇA and NASCIMENTO pairs
    )
    final_data = final_data[final_column_order]

    # Display cleaned data
    st.write("Dados Processados:")
    st.dataframe(final_data)

    # Save DataFrame to an in-memory buffer
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_data.to_excel(writer, index=False, sheet_name="Cleaned Data")
    output.seek(0)

    # Provide a download button
    st.download_button(
        label="Download Cleaned Data",
        data=output,
        file_name="cleaned_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
