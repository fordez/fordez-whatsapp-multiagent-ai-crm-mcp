from datetime import datetime

from whatsapp.agent.services.google_sheet.gspread_helper import (
    get_gspread_client,
    get_spreadsheet_id_from_context,
)
from whatsapp.config import config

# Inicializar cliente gspread usando el módulo compartido
gc = get_gspread_client(service_name="ProjectService")

# Variables de configuración desde config
SHEET_NAME_PROJECTS = config.sheet_name_projects
TIMEZONE = config.timezone


class ProjectService:
    @staticmethod
    def create_project(
        nombre: str,
        id_cliente: str,
        servicio: str = None,
        descripcion: str = None,
        fecha_inicio: str = None,
        fecha_fin: str = None,
        estado: str = "En Progreso",
        nota: str = None,
        ctx=None,
    ) -> dict:
        try:
            if not nombre or not id_cliente:
                return {
                    "success": False,
                    "error": "Campos requeridos: nombre e id_cliente",
                }

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            tz = TIMEZONE
            fecha_creada = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
            project_id = f"PRJ-{datetime.now(tz).strftime('%Y%m%d%H%M%S')}"
            next_row = len(all_records) + 2

            worksheet.update_cell(next_row, 1, project_id)
            worksheet.update_cell(next_row, 2, nombre)
            worksheet.update_cell(next_row, 3, descripcion or "")
            worksheet.update_cell(next_row, 4, servicio or "")
            worksheet.update_cell(next_row, 5, estado)
            worksheet.update_cell(next_row, 6, nota or "")
            worksheet.update_cell(next_row, 7, fecha_inicio or fecha_creada)
            worksheet.update_cell(next_row, 8, fecha_fin or "")
            worksheet.update_cell(next_row, 9, id_cliente)

            return {
                "success": True,
                "project_id": project_id,
                "nombre": nombre,
                "id_cliente": id_cliente,
                "estado": estado,
                "fecha_creada": fecha_creada,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_project_by_id(project_id: str, ctx=None) -> dict:
        try:
            if not project_id:
                return {"success": False, "error": "project_id requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            for row in all_records:
                if str(row.get("Id")) == str(project_id):
                    return {"success": True, "project": row}

            return {
                "success": False,
                "error": f"No se encontró proyecto con ID '{project_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_projects_by_client(id_cliente: str, ctx=None) -> dict:
        try:
            if not id_cliente:
                return {"success": False, "error": "id_cliente requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            projects = [
                row
                for row in all_records
                if str(row.get("Id_Cliente")) == str(id_cliente)
            ]
            return {"success": True, "count": len(projects), "projects": projects}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_project(project_id: str, fields: dict, ctx=None) -> dict:
        if not project_id:
            return {"success": False, "error": "project_id requerido"}
        if not fields:
            return {"success": False, "error": "No se proporcionaron campos"}

        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            col_map = {
                "Id": 1,
                "Nombre": 2,
                "Descripcion": 3,
                "Servicio": 4,
                "Estado": 5,
                "Nota": 6,
                "Fecha_Inicio": 7,
                "Fecha_Fin": 8,
                "Id_Cliente": 9,
            }

            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id")) == str(project_id):
                    for key, value in fields.items():
                        col = col_map.get(key)
                        if col:
                            worksheet.update_cell(idx, col, value)
                    return {
                        "success": True,
                        "project_id": project_id,
                        "updated_fields": list(fields.keys()),
                    }

            return {
                "success": False,
                "error": f"No se encontró proyecto con ID '{project_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_project_note_by_client(id_cliente: str, nota: str, ctx=None) -> dict:
        """Actualiza la nota de todos los proyectos de un cliente."""
        if not id_cliente or not nota:
            return {"success": False, "error": "id_cliente y nota son requeridos"}

        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            updated_count = 0
            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id_Cliente")) == str(id_cliente):
                    worksheet.update_cell(idx, 6, nota)  # Columna 6 es Nota
                    updated_count += 1

            if updated_count == 0:
                return {
                    "success": False,
                    "error": f"No se encontraron proyectos para el cliente '{id_cliente}'",
                }

            return {
                "success": True,
                "id_cliente": id_cliente,
                "updated_projects": updated_count,
                "nota": nota,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_project(project_id: str, ctx=None) -> dict:
        if not project_id:
            return {"success": False, "error": "project_id requerido"}

        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_PROJECTS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id")) == str(project_id):
                    worksheet.delete_rows(idx)
                    return {
                        "success": True,
                        "message": f"Proyecto '{project_id}' eliminado",
                    }

            return {
                "success": False,
                "error": f"No se encontró proyecto con ID '{project_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
