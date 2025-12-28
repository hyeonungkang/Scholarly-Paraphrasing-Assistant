"""메인 UI - Flet"""
import sys
import os
import subprocess

# 가상환경 자동 진입 (크로스 플랫폼 지원)
def restart_in_venv():
    """가상환경이 있으면 자동으로 venv의 Python으로 재실행"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 플랫폼별 Python 실행 파일 경로
    if sys.platform == "win32":
        venv_python = os.path.join(base_path, "venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(base_path, "venv", "bin", "python")
    
    # venv가 있고, 현재 실행 중인 파이썬이 venv의 파이썬이 아니라면
    if os.path.exists(venv_python):
        # 경로 정규화 비교
        current_exe = os.path.normcase(os.path.normpath(sys.executable))
        target_exe = os.path.normcase(os.path.normpath(venv_python))
        
        if current_exe != target_exe:
            print(f"🔄 가상환경으로 재실행합니다: {venv_python}")
            try:
                # sys.argv[0]가 스크립트 경로라면 그대로 전달
                subprocess.check_call([venv_python] + sys.argv)
                sys.exit()
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"⚠️ 가상환경 재실행 실패: {e}")
                print("💡 직접 가상환경을 활성화한 후 실행해주세요.")

# 가상환경 자동 진입 시도 (실패해도 계속 진행)
try:
    restart_in_venv()
except Exception as e:
    print(f"⚠️ 가상환경 체크 중 오류: {e}")
    print("💡 계속 진행합니다...")

import flet as ft
import pyperclip
from graph import analyze
from prompt_generator import register_journal
from storage import (
    get_journals,
    delete_journal,
    get_settings,
    update_setting,
    save_history,
    get_history,
    save_history_list,
)


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Paper Assistant"
        self.page.window.width = 1200
        self.page.window.height = 900
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = ft.Colors.WHITE
        self.page.padding = 0  # Full bleed for sidebar

        self.result = None
        self.selected_journal = None
        self.settings = get_settings()

        # UI State
        self.current_view = "write"  # write, history, settings

        self.build_ui()
        self._prompt_gemini_key_if_missing()

    def build_ui(self):
        # ===== Navigation Rail =====
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.EDIT_OUTLINED,
                    selected_icon=ft.Icons.EDIT,
                    label="작성 & 분석",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS,
                    label="분석 내용",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED,
                    selected_icon=ft.Icons.HISTORY,
                    label="히스토리",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIBRARY_ADD_OUTLINED,
                    selected_icon=ft.Icons.LIBRARY_ADD,
                    label="저널 추가",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="설정",
                ),
            ],
            on_change=self._on_nav_change,
            bgcolor=ft.Colors.GREY_50,
        )

        # ===== Content Area =====
        self.content_area = ft.Container(expand=True, padding=30)
        
        # Initial Views
        self.view_write = self._build_write_view()
        self.view_analysis = self._build_analysis_view()
        self.view_history = self._build_history_view()
        self.view_journal = self._build_journal_register_view()
        self.view_settings = self._build_settings_view()
        
        # Set initial content
        self.content_area.content = self.view_write

        # ===== Main Layout Row =====
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_200),
                    self.content_area,
                ],
                expand=True,
                spacing=0,
            )
        )

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.content_area.content = self.view_write
        elif idx == 1:
            self.content_area.content = self.view_analysis
        elif idx == 2:
            self._refresh_history()
            self.content_area.content = self.view_history
        elif idx == 3:
            self.content_area.content = self.view_journal
        elif idx == 4:
            self.content_area.content = self.view_settings
        self.page.update()

    # ==========================================
    # View Builders
    # ==========================================

    def _build_write_view(self):
        # Input Area
        self.input = ft.TextField(
            label="논문 문단 입력",
            hint_text="분석할 문단을 이곳에 붙여넣으세요...",
            multiline=True,
            min_lines=10,
            max_lines=15,
            expand=True,
            border_radius=12,
            border_color=ft.Colors.GREY_300,
            focused_border_color=ft.Colors.BLUE_600,
            bgcolor=ft.Colors.WHITE,
            text_size=15,
            content_padding=20,
        )

        # Controls (Journal & Options)
        self.journal_dd = ft.Dropdown(
            label="타겟 저널",
            width=250,
            options=self._journal_options(),
            on_select=self._on_journal_change,
            border_radius=10,
            content_padding=15,
            text_size=14,
            border_color=ft.Colors.GREY_300,
        )

        self.ref_toggle = ft.Switch(
            label="문헌 검색 포함",
            value=self.settings.get("enable_references", False),
            on_change=self._on_ref_toggle,
            active_color=ft.Colors.BLUE_600,
        )

        # Action Buttons
        self.analyze_btn = ft.Button(
            "분석 시작",
            icon=ft.Icons.AUTO_AWESOME,
            on_click=self._analyze,
            style=ft.ButtonStyle(
                bgcolor={"": ft.Colors.BLUE_600, "hovered": ft.Colors.BLUE_700},
                color=ft.Colors.WHITE,
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            height=50,
            width=200,
        )

        self.add_journal_btn = ft.IconButton(
            ft.Icons.ADD_CIRCLE_OUTLINE,
            tooltip="새 저널 등록 (Aims & Scope)",
            on_click=self._switch_to_journal_add,
                    icon_color=ft.Colors.BLUE_600,
        )
        
        self.refresh_journal_btn = ft.IconButton(
            ft.Icons.REFRESH,
            tooltip="목록 새로고침",
            on_click=self._reload_journals,
            icon_color=ft.Colors.GREY_500,
        )

        # Tab Contents Containers (Stored to be populated later)
        self.tab_contents = [ft.Column(scroll=ft.ScrollMode.AUTO, spacing=20) for _ in range(6)]
        
        # Tab labels and icons
        tab_labels = [
            ("패러프레이징", ft.Icons.EDIT),
            ("주장 체크", ft.Icons.WARNING_AMBER),
            ("저널 매칭", ft.Icons.ASSIGNMENT_TURNED_IN),
            ("주장 확장", ft.Icons.EXTENSION),
            ("참고문헌", ft.Icons.BOOK),
            ("리뷰어 Q&A", ft.Icons.QUESTION_ANSWER),
        ]
        
        # Create tab buttons
        self.tab_buttons = []
        for i, (label, icon) in enumerate(tab_labels):
            btn = ft.Button(
                label,
                icon=icon,
                on_click=lambda e, idx=i: self._switch_tab(idx),
            style=ft.ButtonStyle(
                    bgcolor={"": ft.Colors.BLUE_600 if i == 0 else ft.Colors.GREY_300},
                    color={"": ft.Colors.WHITE if i == 0 else ft.Colors.BLACK87},
                ),
            )
            self.tab_buttons.append(btn)
        
        self.selected_tab_index = 0
        
        # Tab buttons row container
        self.result_tabs_container = ft.Container(
            content=ft.Row(
                controls=self.tab_buttons,
                spacing=5,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.all(10),
            bgcolor=ft.Colors.WHITE,
            border_radius=10,
            visible=False,
        )

        # Result container
        self.result_container = ft.Container(
            content=self.tab_contents[0],
            visible=False,
            expand=True,
        )

        # Loading & Status
        self.loading = ft.ProgressRing(visible=False, width=25, height=25, stroke_width=3, color=ft.Colors.BLUE_600)
        self.status_text = ft.Text("", size=14, color=ft.Colors.BLUE_GREY)
        
        # Translation result display
        self.translation_text = ft.Text(
            "",
            size=14,
            selectable=True,
        )
        self.translation_status = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_600,
            italic=True,
        )
        self.translation_display = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.TRANSLATE, size=18, color=ft.Colors.BLUE_600),
                        ft.Text("한국어 번역", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                    ], spacing=8),
                    ft.Container(expand=True),
                ft.IconButton(
                        ft.Icons.COPY,
                        icon_size=18,
                        tooltip="번역 결과 복사",
                        on_click=lambda e: self._copy(self.translation_text.value) if self.translation_text.value else None,
                    ),
                ]),
                self.translation_status,
                ft.Container(
                    content=self.translation_text,
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.BLUE_200),
                ),
            ], spacing=8),
            visible=False,
        )

        # Assemble Write View
        return ft.Container(
            content=ft.Column(
                controls=[
                    # Top Bar Area
                    ft.Row(
                        [
                            ft.Text("Paper Assistant", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                            ft.Container(expand=True),
                self.status_text,
                            self.loading,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    
                    # Input Section
            ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("Source Text", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                                ft.Container(expand=True),
                                ft.Text("Ctrl + Enter to Analyze", size=12, color=ft.Colors.GREY_400),
                            ]),
                            self.input,
                            self.translation_display,
                            ft.Row([
                                self.journal_dd,
                                self.add_journal_btn,
                                self.refresh_journal_btn,
                                ft.Container(width=20),
                                self.ref_toggle,
                                ft.Container(expand=True),
                                ft.TextButton("Clear", icon=ft.Icons.CLEAR_ALL, on_click=self._clear_input, style=ft.ButtonStyle(color=ft.Colors.GREY_500)),
                                self.analyze_btn,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ], spacing=10),
                        expand=True, 
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=30,
        )

    def _build_analysis_view(self):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Analysis Result", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.result_tabs_container,
                        ft.Container(
                        content=self.result_container,
                            expand=True,
                        padding=10,
                            bgcolor=ft.Colors.WHITE,
                            border_radius=10,
                    )
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=30,
        )

    def _build_history_view(self):
        self.history_list = ft.ListView(expand=True, spacing=10)
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("History", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.history_list,
                ],
                expand=True,
            ),
            padding=20,
        )

    def _build_settings_view(self):
        # Settings fields will be created here
        self.settings_col = ft.Column(spacing=20)
        self._refresh_settings_view()
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                    self.settings_col
                    ],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
        )

    # ==========================================
    # Logic & Events
    # ==========================================

    def _switch_tab(self, index: int):
        """탭 전환"""
        self.selected_tab_index = index
        self.result_container.content = self.tab_contents[index]
        
        # 버튼 스타일 업데이트
        for i, btn in enumerate(self.tab_buttons):
            if i == index:
                btn.style.bgcolor = {"": ft.Colors.BLUE_600}
                btn.style.color = {"": ft.Colors.WHITE}
            else:
                btn.style.bgcolor = {"": ft.Colors.GREY_300}
                btn.style.color = {"": ft.Colors.BLACK87}
        
        self.page.update()

    async def _do_analyze(self):
        text = self.input.value
        if not text or not text.strip():
            self._snack("⚠️ 문단을 입력하세요", bgcolor=ft.Colors.ORANGE)
            return

        # Check API Key
        from config import GEMINI_API_KEY
        api_key = GEMINI_API_KEY or self.settings.get("gemini_api_key", "")
        if not api_key:
            self._snack("⚠️ Gemini API 키가 필요합니다. 설정 메뉴를 확인하세요.", bgcolor=ft.Colors.RED)
            self._prompt_gemini_key_if_missing()
            return

        self.analyze_btn.disabled = True
        self.loading.visible = True
        self.status_text.value = "AI 분석 중..."
        self.page.update()

        try:
            j_name = self.selected_journal["name"] if self.selected_journal else ""
            self.result = await analyze(text.strip(), j_name)

            # Update translation display
            translation = self.result.get("translation")
            translation_skipped = self.result.get("translation_skipped_korean", False)
            translation_error = self.result.get("translation_error", False)
            
            if translation:
                # 번역 성공
                self.translation_text.value = translation
                self.translation_status.value = "✓ 영어 입력을 한국어로 번역했습니다."
                self.translation_status.color = ft.Colors.GREEN_600
                self.translation_display.visible = True
            elif translation_skipped:
                # 한국어 입력이므로 번역 건너뜀 (정상)
                self.translation_text.value = ""
                self.translation_status.value = "ℹ 입력이 한국어이므로 번역을 건너뜁니다."
                self.translation_status.color = ft.Colors.BLUE_600
                self.translation_display.visible = True
            elif translation_error:
                # 번역 실패
                self.translation_text.value = ""
                self.translation_status.value = "⚠ 번역에 실패했습니다."
                self.translation_status.color = ft.Colors.ORANGE_600
                self.translation_display.visible = True
            else:
                # 번역 노드가 실행되지 않음 (이론적으로 발생하지 않아야 함)
                self.translation_display.visible = False

            # Update Tabs
            self._show_paraphrases()
            self._show_claim()
            self._show_journal()
            self._show_expand()
            self._show_refs()
            self._show_reviewer()
            
            # Show Results
            self.result_tabs_container.visible = True
            self.result_container.visible = True
            
            # Switch to Analysis View
            self.current_view = "analysis"
            self.rail.selected_index = 1
            self.content_area.content = self.view_analysis
            self.page.update()

            # Default to first tab
            self._switch_tab(0)

            save_history(text, self.result)
            
            # #region agent log - debug result structure
            try:
                print("\n[Analysis Result Debug]")
                print(f"Keys: {list(self.result.keys())}")
                if self.result.get("journal_match"):
                    print(f"Journal Match Score: {self.result['journal_match'].get('score')}")
                if self.result.get("claim"):
                    print(f"Claim Score: {self.result['claim'].get('score')}")
            except: pass
            # #endregion

            self.status_text.value = "분석 완료"
            self._snack("✅ 분석이 완료되었습니다!", bgcolor=ft.Colors.GREEN)

        except Exception as ex:
            error_msg = str(ex)
            self.status_text.value = "오류 발생"
            self._snack(f"❌ 분석 실패: {error_msg}", bgcolor=ft.Colors.RED)
            print(f"Error: {ex}")
        finally:
            self.analyze_btn.disabled = False
            self.loading.visible = False
            self.page.update()

    def _analyze(self, e):
        self.page.run_task(self._do_analyze)

    def _clear_input(self, e):
        self.input.value = ""
        self.status_text.value = ""
        self.result = None
        self.translation_text.value = ""
        self.translation_status.value = ""
        self.translation_display.visible = False
        self.page.update()

    # ==========================================
    # Journal & Dialogs
    # ==========================================

    def _journal_options(self):
        opts = [ft.dropdown.Option(key="", text="선택 안함 (일반 분석)")]
        for j in get_journals():
            opts.append(ft.dropdown.Option(key=j["name"], text=j["name"]))
        return opts
    
    def _reload_journals(self, e=None):
        self.journal_dd.options = self._journal_options()
        self.journal_dd.value = ""
        self.selected_journal = None
        self.page.update()
        self._snack("저널 목록 동기화 완료")

    def _on_journal_change(self, e):
        name = e.control.value
        if name:
            journals = get_journals()
            self.selected_journal = next((j for j in journals if j["name"] == name), None)
        else:
            self.selected_journal = None

    def _build_journal_register_view(self):
        name_field = ft.TextField(
            label="저널 약어 (예: IEEE TII)", 
            label_style=ft.TextStyle(size=12, color=ft.Colors.BLUE_GREY_400),
            border_radius=8, bgcolor=ft.Colors.GREY_50, filled=True, border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.BLUE_600,
        )
        full_field = ft.TextField(
            label="저널 전체 이름", 
            label_style=ft.TextStyle(size=12, color=ft.Colors.BLUE_GREY_400),
            border_radius=8, bgcolor=ft.Colors.GREY_50, filled=True, border_color=ft.Colors.TRANSPARENT,
             focused_border_color=ft.Colors.BLUE_600,
        )
        scope_field = ft.TextField(
            label="Aims & Scope",
            hint_text="저널 홈페이지의 Aims & Scope 섹션을 그대로 복사해서 붙여넣으세요.",
            multiline=True, min_lines=5, max_lines=15,
            label_style=ft.TextStyle(size=12, color=ft.Colors.BLUE_GREY_400),
            border_radius=8, bgcolor=ft.Colors.GREY_50, filled=True, border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.BLUE_600,
        )
        method_field = ft.TextField(
            label="추가 요구사항 (옵션)",
            hint_text="예: 통계적 검증을 엄격하게 봅니다.",
            multiline=True, min_lines=2,
            label_style=ft.TextStyle(size=12, color=ft.Colors.BLUE_GREY_400),
            border_radius=8, bgcolor=ft.Colors.GREY_50, filled=True, border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ft.Colors.BLUE_600,
        )
        
        status = ft.Text("", size=12)
        loading_indicator = ft.ProgressRing(visible=False, width=20, height=20)

        async def _save():
            if not name_field.value or not scope_field.value:
                status.value = "⚠️ 약어와 Aims & Scope는 필수입니다."
                status.color = ft.Colors.RED_400
                status.update()
                return

            # 로딩 상태 시작
            loading_indicator.visible = True
            status.value = "🔄 맞춤 프롬프트 생성 중..."
            status.color = ft.Colors.BLUE_600
            
            # 모든 입력 필드와 버튼 비활성화
            name_field.disabled = True
            full_field.disabled = True
            scope_field.disabled = True
            method_field.disabled = True
            save_button.disabled = True
            
            self.page.update()

            try:
                # Store the name to use in the message before clearing
                saved_name = name_field.value.strip()
                await register_journal(
                    name=saved_name,
                    full_name=full_field.value.strip() or saved_name,
                    aims_scope=scope_field.value.strip(),
                    custom_methodology=method_field.value.strip(),
                )
                self._reload_journals()
                
                # Clear fields
                name_field.value = ""
                full_field.value = ""
                scope_field.value = ""
                method_field.value = ""
                status.value = ""
                
                # 로딩 상태 종료 및 모든 요소 활성화
                loading_indicator.visible = False
                name_field.disabled = False
                full_field.disabled = False
                scope_field.disabled = False
                method_field.disabled = False
                save_button.disabled = False

                self.page.update()
                self._snack(f"✅ '{saved_name}' 등록 완료. 이제 목록에서 선택할 수 있습니다.", bgcolor=ft.Colors.GREEN)
                # Switch back to write view
                self.rail.selected_index = 0
                self.content_area.content = self.view_write
                self.page.update()
            except Exception as ex:
                # #region agent log
                import json
                import traceback
                try:
                    with open(r'c:\Users\khw95\OneDrive\문서\paper_assistance\paragraph-reviewer\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "main.py:627", "message": "journal registration exception", "data": {"error": str(ex), "error_type": type(ex).__name__, "traceback": traceback.format_exc()}, "timestamp": __import__('time').time() * 1000}) + '\n')
                except: pass
                # #endregion
                status.value = f"Error: {ex}"
                status.color = ft.Colors.RED
                
                # 로딩 상태 종료 및 모든 요소 활성화
                loading_indicator.visible = False
                name_field.disabled = False
                full_field.disabled = False
                scope_field.disabled = False
                method_field.disabled = False
                save_button.disabled = False
                
                status.update()

        def _save_click(e):
             self.page.run_task(_save)
        
        # 버튼 생성 (함수 내에서 참조 가능하도록)
        save_button = ft.Button(
            "저널 등록하기", 
            icon=ft.Icons.SAVE,
            on_click=_save_click, 
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600, 
                color=ft.Colors.WHITE,
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=10)
            ),
            height=50,
        )

        return ft.Container(
                content=ft.Column(
                    [
                    ft.Text("Target Journal Registration", size=24, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                    ft.Text("저널의 Aims & Scope를 등록하면 AI가 해당 관점에서 리뷰합니다.", size=14, color=ft.Colors.GREY_600),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                        name_field,
                        full_field,
                        scope_field,
                        method_field,
                    ft.Row([
                        status,
                        loading_indicator,
                    ], spacing=10),
                    ft.Container(height=10),
                    save_button,
                    ft.Divider(height=30),
                    ft.Text("저널 관리", size=20, weight=ft.FontWeight.BOLD),
                    self._build_journal_list(),
                ],
                    scroll=ft.ScrollMode.AUTO,
                spacing=15,
            ),
            padding=30,
        )

    def _build_journal_list(self):
        """저널 목록 및 삭제 버튼 생성"""
        journals = get_journals()
        
        if not journals:
             return ft.Text("등록된 저널이 없습니다.", color=ft.Colors.GREY_400)

        list_col = ft.Column(spacing=10)
        
        for j in journals:
            list_col.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Column([
                            ft.Text(j["name"], weight="bold", size=16),
                            ft.Text(j.get("full_name", ""), size=12, color=ft.Colors.GREY_600),
                        ]),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE, 
                            icon_color=ft.Colors.RED_400,
                            tooltip="삭제",
                            on_click=lambda e, name=j["name"]: self._delete_journal_click(name)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15,
                    border=ft.Border.all(1, ft.Colors.GREY_200),
                    border_radius=8,
                    bgcolor=ft.Colors.WHITE,
                )
            )
        return list_col

    def _delete_journal_click(self, name):
        """저널 삭제 핸들러"""
        # Dialog handle for closing
        dlg_modal = ft.AlertDialog(
            title=ft.Text("저널 삭제"),
            content=ft.Text(f"정말로 '{name}' 저널을 삭제하시겠습니까?"),
            actions=[
                ft.TextButton("취소", on_click=lambda e: self._close_dialog(dlg_modal)),
                ft.TextButton(
                    "삭제", 
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                    on_click=lambda e: self._confirm_delete(name, dlg_modal)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(dlg_modal)
        dlg_modal.open = True
        self.page.update()

    def _close_dialog(self, dlg):
        """다이얼로그 닫기"""
        dlg.open = False
        self.page.update()

    def _confirm_delete(self, name, dlg):
        try:
            delete_journal(name)
            self._close_dialog(dlg)
            self._snack(f"'{name}' 저널이 삭제되었습니다.")
            
            # Refresh related views
            self.journal_dd.options = self._journal_options()
            self.view_journal = self._build_journal_register_view()
            
            # If currently viewing the journal add page, refresh it in place
            if self.rail.selected_index == 3:
                self.content_area.content = self.view_journal
            
            self.page.update()
        except Exception as ex:
            print(f"Delete Error: {ex}")
            self._close_dialog(dlg)

    def _switch_to_journal_add(self, e=None):
        self.rail.selected_index = 3
        self.content_area.content = self.view_journal
        self.page.update()
            
    # ==========================================
    # Display Logic (Tabs) - Ported & Styled
    # ==========================================
    
    def _card(self, title, content, color=ft.Colors.GREY_50):
        return ft.Container(
            ft.Column([
                ft.Row([
                    ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                    ft.IconButton(ft.Icons.COPY, icon_size=18, on_click=lambda e: self._copy(content.__str__()), tooltip="복사")
                ], alignment="spaceBetween"),
                ft.Container(
                    ft.Text(str(content), size=14, color=ft.Colors.GREY_800, selectable=True),
                    width=None,  # 부모 너비에 맞춤
                ),
            ], spacing=5),
            padding=15,
            bgcolor=color,
            border_radius=10,
            border=ft.Border.all(1, ft.Colors.GREY_100),
        )

    def _show_paraphrases(self):
        c = self.tab_contents[0]
        c.controls.clear()
        
        if not self.result or not self.result.get("paraphrases"):
             c.controls.append(ft.Text("분석 결과가 없습니다."))
             return

        # Section 정보 표시 및 paraphrases 데이터 처리
        paraphrases_data = self.result.get("paraphrases", {})
        section = None
        styles_list = []
        
        if isinstance(paraphrases_data, dict):
            section = paraphrases_data.get("section")
            styles_list = paraphrases_data.get("styles", [])
        elif isinstance(paraphrases_data, list):
            # 하위 호환성: 리스트인 경우 그대로 사용
            styles_list = paraphrases_data
        
        if section:
            c.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.BLUE_600, size=16),
                        ft.Text(f"Section: {section}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                    ]),
                    padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=8, margin=ft.Margin.only(bottom=10)
                )
            )

        c.controls.append(ft.Text("💡 더 나은 표현 제안", weight=ft.FontWeight.BOLD, size=16))

        # 번역 결과 가져오기 (global)
        global_translation = self.result.get("translation")
        
        # 카드들 렌더링 (각 카드 밑에 번역 표시)
        for s in styles_list:
            if isinstance(s, dict):
                # 스타일 카드 추가
                c.controls.append(self._card(s.get("name", "Option"), s.get("text", "")))
                
                # 번역 버블 추가 (개별 번역 우선, 없으면 글로벌 번역)
                # 이제 프롬프트가 개별 번역을 제공하도록 업데이트되었으므로 s.get("translation")이 존재할 가능성이 높음
                style_translation = s.get("translation")
                
                # 표시할 번역이 있는 경우에만 표시
                display_trans = style_translation if style_translation else global_translation
                
                if display_trans:
                    c.controls.append(
                        ft.Container(
                            ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.TRANSLATE, size=16, color=ft.Colors.BLUE_600),
                                    ft.Text("한국어 번역", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        ft.Icons.COPY,
                                        icon_size=16,
                                        tooltip="번역 결과 복사",
                                        on_click=lambda e, t=display_trans: self._copy(t),
                                    ),
                                ]),
                                ft.Container(
                                    ft.Text(display_trans, selectable=True, size=13),
                                    padding=12,
                                    bgcolor=ft.Colors.BLUE_50,
                                    border_radius=6,
                                    border=ft.Border.all(1, ft.Colors.BLUE_200),
                                    width=None,
                                ),
                            ], spacing=6),
                            margin=ft.Margin.only(top=8, bottom=15)
                        )
                    )

    def _show_claim(self):
        c = self.tab_contents[1]
        c.controls.clear()
        
        # 결과가 없거나 claim 필드가 없는 경우
        if not self.result:
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.GREY_400),
                        ft.Text("분석 결과가 없습니다.", size=16, color=ft.Colors.GREY_600, weight=ft.FontWeight.BOLD),
                        ft.Text("문단을 입력하고 분석을 시작하세요.", size=14, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                        alignment=ft.alignment.Alignment(0, 0),
                )
            )
            return
        
        data = self.result.get("claim", {})
        if not data or not isinstance(data, dict):
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.WARNING_AMBER, size=48, color=ft.Colors.ORANGE_400),
                        ft.Text("주장 체크 결과를 불러올 수 없습니다.", size=16, color=ft.Colors.GREY_600, weight=ft.FontWeight.BOLD),
                        ft.Text("분석을 다시 시도해주세요.", size=14, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                        alignment=ft.alignment.Alignment(0, 0),
                )
            )
            return
            
        score = data.get("score", 0)
        c.controls.append(
            ft.Container(
                ft.Column([
                    ft.Text("과대해석 위험도", size=12, color=ft.Colors.GREY_600),
                    ft.Row([
                        ft.ProgressBar(value=score/10, color=ft.Colors.RED if score > 5 else ft.Colors.GREEN, expand=True),
                        ft.Text(f"{score}/10", weight=ft.FontWeight.BOLD, selectable=True),
                    ], alignment="center"),
                ]),
                padding=15, border=ft.Border.all(1, ft.Colors.GREY_200), border_radius=10
            )
        )
        
        # Section 정보 표시
        section = data.get("section")
        if section:
            c.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.BLUE_600, size=16),
                        ft.Text(f"Section: {section}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                    ]),
                    padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=8, margin=ft.Margin.only(top=10, bottom=10)
                )
            )
        
        claim_text = data.get("claim", "")
        # claim은 이제 항상 존재해야 함 (fallback 로직으로 인해)
        c.controls.append(
            ft.Text("핵심 주장", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.BLACK87, margin=ft.Margin.only(top=15, bottom=8))
        )
        c.controls.append(
            ft.Container(
                ft.Text(claim_text if claim_text else "주장 추출 중...", selectable=True, size=14, color=ft.Colors.BLACK87),
                padding=15, bgcolor=ft.Colors.WHITE, border_radius=8, width=None,
                border=ft.Border.all(1, ft.Colors.BLUE_300),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=ft.Colors.BLUE_100, offset=ft.Offset(0, 2))
            )
        )
        
        if data.get("issues"):
            c.controls.append(
                ft.Text("발견된 문제점", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.RED_600, margin=ft.Margin.only(top=20, bottom=10))
            )
            for issue in data.get("issues", []):
                c.controls.append(
                    ft.Container(
                        ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_600, size=18), 
                            ft.Container(
                                ft.Text(issue, expand=True, selectable=True, size=14, color=ft.Colors.BLACK87),
                                width=None, padding=ft.Padding.only(left=8)
                            )
                        ], wrap=True),
                        padding=12, 
                        bgcolor=ft.Colors.RED_50,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.RED_200),
                        margin=ft.Margin.only(bottom=8)
                    )
                )
        
        if data.get("suggestions"):
            c.controls.append(
                ft.Text("수정 제안", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.GREEN_700, margin=ft.Margin.only(top=20, bottom=10))
            )
            for sug in data.get("suggestions", []):
                c.controls.append(
                    ft.Container(
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_700, size=18), 
                            ft.Container(
                                ft.Text(sug, expand=True, selectable=True, size=14, color=ft.Colors.BLACK87),
                                width=None, padding=ft.Padding.only(left=8)
                            )
                        ], wrap=True),
                        padding=12,
                        bgcolor=ft.Colors.GREEN_50,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.GREEN_200),
                        margin=ft.Margin.only(bottom=8)
                    )
                )

    def _show_journal(self):
        c = self.tab_contents[2]
        c.controls.clear()
        data = self.result.get("journal_match")
        if not data:
            c.controls.append(ft.Text("저널 매칭 분석 결과가 없습니다 (저널 미선택 등).", color=ft.Colors.GREY_400))
            return

        # Section 정보 표시
        section = data.get("section")
        if section:
            c.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.BLUE_600, size=16),
                        ft.Text(f"Section: {section}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                    ]),
                    padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=8, margin=ft.Margin.only(bottom=10)
                )
            )

        score = data.get("score", 0)
        # 0-10점 척도 대응
        color = ft.Colors.GREEN if score >= 7 else (ft.Colors.ORANGE if score >= 4 else ft.Colors.RED)

        c.controls.append(
            ft.Container(
                ft.Row([
                    ft.Column([
                         ft.Text("저널 적합도", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87, selectable=True),
                         ft.Text(f"{score}점", size=28, weight=ft.FontWeight.BOLD, color=color, selectable=True),
                    ]),
                    ft.Container(width=20),
                    ft.Column([
                        ft.Text("✅ 일치하는 점", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLACK87),
                        *[ft.Container(
                            ft.Text(f"• {m}", size=13, selectable=True, color=ft.Colors.BLACK87),
                            width=None,
                            padding=ft.Padding.only(top=4, bottom=4)
                        ) for m in data.get("matches", [])]
                    ], expand=True),
                ]),
                padding=20, bgcolor=ft.Colors.WHITE, border_radius=12,
                border=ft.Border.all(1, ft.Colors.BLUE_300),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=ft.Colors.BLUE_100, offset=ft.Offset(0, 2))
            )
        )
        
        if data.get("gaps"):
            c.controls.append(
                ft.Text("보완이 필요한 부분", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.RED_600, margin=ft.Margin.only(top=20, bottom=10))
            )
            for gap in data.get("gaps", []):
                c.controls.append(
                    ft.Container(
                        ft.Row([
                            ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE, color=ft.Colors.RED_600, size=18), 
                            ft.Container(
                                ft.Text(gap, selectable=True, expand=True, size=13, color=ft.Colors.BLACK87),
                                width=None, padding=ft.Padding.only(left=8)
                            )
                        ], wrap=True),
                        padding=12,
                        bgcolor=ft.Colors.RED_50,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.RED_200),
                        margin=ft.Margin.only(bottom=8)
                    )
                )
        
        if data.get("revised"):
            c.controls.append(ft.Divider())
            c.controls.append(self._card("저널 스타일에 맞춘 수정본 (한국어)", data.get("revised")))

        if data.get("revised_en"):
            c.controls.append(ft.Divider())
            c.controls.append(self._card("저널 스타일에 맞춘 수정본 (English)", data.get("revised_en")))

    def _build_expansion_card(self, data, idx):
        """Builds a single expansion card with cleaner UI"""
        claim_text = data.get('claim', '')
        pro_text = data.get('pro', '')
        con_text = data.get('con', '')
        reason_text = data.get('reason', '')
        experiments_list = data.get('experiments', [])
        type_text = data.get('type', f'Strategy {idx + 1}')

        # Colors based on index to give variety or consistent blue
        header_color = ft.Colors.BLUE_700
        icon_color = ft.Colors.BLUE_600
        bg_color = ft.Colors.WHITE

        return ft.Container(
            content=ft.Column([
                # 1. Header: Type
                ft.Row([
                    ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.AMBER_600, size=24),
                    ft.Text(type_text, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                
                ft.Divider(height=20, color=ft.Colors.GREY_200),

                # 2. Main Claim (Hero Box)
                ft.Container(
                    content=ft.Column([
                        ft.Text("UPGRADED CLAIM", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                        ft.Text(
                            claim_text if claim_text else "(No Claim Generated)", 
                            size=16, 
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.BLACK87, 
                            selectable=True,
                            italic=not bool(claim_text)
                        ),
                    ], spacing=5),
                    padding=15,
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.BLUE_100),
                    width=None,
                ),

                ft.Container(height=10),

                # 3. Why & Analysis (Grid-like layout using Rows/Cols)
                ft.Text("ANALYSIS", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                ft.Container(
                    content=ft.Column([
                        # Reason
                        ft.Row([
                            ft.Icon(ft.Icons.FORMAT_QUOTE_ROUNDED, size=16, color=ft.Colors.GREY_500),
                            ft.Container(
                                ft.Text(reason_text, size=14, color=ft.Colors.GREY_800, selectable=True),
                                expand=True
                            )
                        ], vertical_alignment=ft.CrossAxisAlignment.START),
                        
                        ft.Divider(height=10, color=ft.Colors.GREY_100),
                        
                        # Pros / Cons
                        ft.Row([
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([ft.Icon(ft.Icons.ADD_CIRCLE, size=14, color=ft.Colors.GREEN_600), ft.Text("Pros", size=12, color=ft.Colors.GREEN_700, weight="bold")]),
                                    ft.Text(pro_text, size=13, color=ft.Colors.GREY_800)
                                ]),
                                expand=True
                            ),
                            ft.Container(width=10),
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([ft.Icon(ft.Icons.REMOVE_CIRCLE, size=14, color=ft.Colors.RED_600), ft.Text("Cons", size=12, color=ft.Colors.RED_700, weight="bold")]),
                                    ft.Text(con_text, size=13, color=ft.Colors.GREY_800)
                                ]),
                                expand=True
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.START)
                    ], spacing=10),
                    padding=15,
                    border=ft.Border.all(1, ft.Colors.GREY_200),
                    border_radius=8,
                ),

                ft.Container(height=10),

                # 4. Experiments (Checklist style)
                ft.Text("REQUIRED EXPERIMENTS", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_BOX_OUTLINED, size=16, color=ft.Colors.PURPLE_500),
                            ft.Container(ft.Text(exp, size=14, selectable=True), expand=True)
                        ], vertical_alignment=ft.CrossAxisAlignment.START) 
                        for exp in experiments_list
                    ] if experiments_list else [ft.Text("(No experiments suggested)", size=14, color=ft.Colors.GREY_500, italic=True)], spacing=8),
                    padding=15,
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.PURPLE_100),
                )
            ], spacing=5),
            padding=25,
            bgcolor=bg_color,
            border_radius=12,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                offset=ft.Offset(0, 4)
            ),
            margin=ft.Margin.only(bottom=20)
        )

    def _show_expand(self):
        c = self.tab_contents[3]
        c.controls.clear()

        # 결과가 없는 경우
        if not self.result:
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.GREY_400),
                        ft.Text("분석 결과가 없습니다.", size=16, color=ft.Colors.GREY_600, weight=ft.FontWeight.BOLD),
                        ft.Text("문단을 입력하고 분석을 시작하세요.", size=14, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    alignment=ft.alignment.Alignment(0, 0),
                )
            )
            return
        
        expansions = self.result.get("expansions", [])
        
        # 확장 결과가 없는 경우
        if not expansions or not isinstance(expansions, list) or len(expansions) == 0:
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=48, color=ft.Colors.AMBER_400),
                        ft.Text("주장 확장 결과가 없습니다.", size=16, color=ft.Colors.GREY_600, weight=ft.FontWeight.BOLD),
                        ft.Text("주장 체크가 완료된 후 확장 제안이 생성됩니다.", size=14, color=ft.Colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    alignment=ft.alignment.Alignment(0, 0),
                )
            )
            return

        # Header Section
        header_controls = []
        
        # Section Info
        first_exp = expansions[0]
        if isinstance(first_exp, dict) and "section" in first_exp:
            section = first_exp.get("section")
            if section:
                header_controls.append(
                    ft.Container(
                        ft.Row([
                            ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.BLUE_600, size=16),
                            ft.Text(f"Section: {section}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                        ]),
                        padding=10, bgcolor=ft.Colors.BLUE_50, border_radius=8
                    )
                )

        # Title
        header_controls.append(
            ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, color=ft.Colors.BLUE_700, size=24),
                ft.Text("Research Upgrade Proposals", weight=ft.FontWeight.BOLD, size=20, color=ft.Colors.BLUE_800),
            ], spacing=10)
        )
        
        header_controls.append(
            ft.Text("AI가 제안하는 3-4가지 Next Level 연구 방향입니다.", size=14, color=ft.Colors.GREY_600)
        )

        c.controls.append(ft.Column(header_controls, spacing=10))
        c.controls.append(ft.Divider(height=30, color=ft.Colors.TRANSPARENT))

        # Cards
        for idx, d in enumerate(expansions):
            if not isinstance(d, dict): continue
            
            # essential check
            if not d.get('claim') and not d.get('pro'): continue
            
            c.controls.append(self._build_expansion_card(d, idx))
        
        # 번역 결과 표시 (카드들 아래에)
        translation = self.result.get("translation")
        if translation:
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.TRANSLATE, size=18, color=ft.Colors.BLUE_600),
                            ft.Text("한국어 번역", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                            ft.Container(expand=True),
                            ft.IconButton(
                                ft.Icons.COPY,
                                icon_size=18,
                                tooltip="번역 결과 복사",
                                on_click=lambda e: self._copy(translation),
                            ),
                        ]),
                        ft.Container(
                            ft.Text(translation, selectable=True, size=14),
                            padding=15,
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=8,
                            border=ft.Border.all(1, ft.Colors.BLUE_200),
                        ),
                    ], spacing=8),
                    margin=ft.Margin.only(top=15)
                )
            )

    def _extract_doi_from_bibtex(self, bibtex: str) -> str:
        """BibTeX에서 DOI 추출"""
        import re
        match = re.search(r'doi\s*=\s*\{([^}]+)\}', bibtex, re.IGNORECASE)
        if match:
            return match.group(1)
        return ""

    def _show_refs(self):
        c = self.tab_contents[4]
        c.controls.clear()
        refs = self.result.get("references", [])
        if not refs:
            c.controls.append(ft.Text("추천된 참고문헌이 없습니다."))
            return

        for r in refs:
            doi = r.get("doi", "")
            bibtex = r.get("bibtex", "")
            if not doi and bibtex:
                doi = self._extract_doi_from_bibtex(bibtex)
            
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Text(r.get("title"), weight="bold", size=14, selectable=True),
                        ft.Text(f"{r.get('authors')} ({r.get('year')}) - {r.get('venue')}", size=12, color=ft.Colors.GREY_600, selectable=True),
                        ft.Text(f"In-context Citation: {r.get('citations')} citations", size=11, color=ft.Colors.BLUE_400, selectable=True),
                        ft.Row([
                            ft.TextButton("DOI Link", on_click=lambda e, u=r.get("doi_url"): self.page.launch_url(u)) if r.get("doi_url") else ft.Container(),
                            ft.IconButton(ft.Icons.COPY, tooltip="Copy DOI", on_click=lambda e, d=doi: self._copy(d)) if doi else ft.Container(),
                            ft.IconButton(ft.Icons.COPY, tooltip="Copy BibTeX", on_click=lambda e, b=bibtex: self._copy(b)) if bibtex else ft.Container(),
                        ])
                    ]),
                    padding=15, bgcolor=ft.Colors.GREY_50, border_radius=8, margin=ft.Margin.only(bottom=10)
                )
            )

    def _show_reviewer(self):
        c = self.tab_contents[5]
        c.controls.clear()

        # Section 정보 표시
        section = self.result.get("reviewer_section")
        if not section:
            # reviewer_qs에서 section 추출 시도
            reviewer_qs = self.result.get("reviewer_qs", [])
            if reviewer_qs and isinstance(reviewer_qs, list) and len(reviewer_qs) > 0:
                first_q = reviewer_qs[0]
                if isinstance(first_q, dict) and "section" in first_q:
                    section = first_q.get("section")
        
        if section:
            c.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Icon(ft.Icons.BOOKMARK, color=ft.Colors.BLUE_600, size=16),
                        ft.Text(f"Section: {section}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                    ]),
                    padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=8, margin=ft.Margin.only(bottom=10)
                )
            )
        
        # 긍정적인 칭찬 표시 (먼저 표시)
        positive_feedback = self.result.get("positive_feedback")
        if positive_feedback:
            c.controls.append(
                            ft.Container(
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.THUMB_UP, color=ft.Colors.GREEN_600, size=18),
                            ft.Text("긍정적인 피드백", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700, size=14)
                        ], spacing=8),
                        ft.Container(
                            ft.Text(positive_feedback, selectable=True, size=13),
                            width=None
                        ),
                    ], spacing=8),
                    padding=15, bgcolor=ft.Colors.GREEN_50, border_radius=8, 
                    border=ft.Border.all(2, ft.Colors.GREEN_200),
                    margin=ft.Margin.only(bottom=15)
                )
            )
        
        # 질문들 표시
        for q in self.result.get("reviewer_qs", []):
            if not isinstance(q, dict):
                continue
            color = ft.Colors.RED_100 if q.get("severity") == "critical" else ft.Colors.ORANGE_50
            c.controls.append(
                ft.Container(
                    ft.Column([
                        ft.Container(
                            ft.Text(f"Q. {q.get('q')}", weight="bold", selectable=True),
                            width=None
                        ),
                        ft.Container(
                            ft.Text(f"Why? {q.get('reason')}", size=12, color=ft.Colors.GREY_700, selectable=True),
                            width=None
                        ),
                    ]),
                    padding=15, bgcolor=color, border_radius=8, margin=ft.Margin.only(bottom=10)
                )
            )

    # ==========================================
    # Settings & History Views
    # ==========================================
    
    def _refresh_history(self):
        self.history_list.controls.clear()
        for idx, item in enumerate(get_history()):
            text_prev = item.get("text", "")[:80] + "..."
            self.history_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ARTICLE),
                    title=ft.Text(text_prev),
                    subtitle=ft.Text(item.get("time", "")),
                    trailing=ft.IconButton(ft.Icons.DELETE, on_click=lambda e, i=item: self._delete_history(i)),
                    on_click=lambda e, r=item.get("result"): self._load_from_history(r)
                )
            )
    
    def _delete_history(self, item):
         history = get_history()
         new_h = [h for h in history if h.get("time") != item.get("time")]
         save_history_list(new_h)
         self._refresh_history()
         self.page.update()

    def _load_from_history(self, result):
        self.result = result
        self.current_view = "analysis"
        self.rail.selected_index = 1
        self.content_area.content = self.view_analysis
        
        self._show_paraphrases()
        self._show_claim()
        self._show_journal()
        self._show_reviewer()
        self._show_expand()
        self._show_refs()
        self.result_tabs_container.visible = True
        self.result_container.visible = True
        
        # Default to first tab if not set
        if self.result_container.content is None:
             self._switch_tab(0)
             
        self.page.update()

    def _refresh_settings_view(self):
        self.settings_col.controls.clear()
        
        gemini_key = ft.TextField(label="Gemini API Key", value=self.settings.get("gemini_api_key", ""), password=True, can_reveal_password=True, width=500)
        ss_key = ft.TextField(label="Semantic Scholar API Key", value=self.settings.get("ss_api_key", ""), password=True, can_reveal_password=True, width=500)
        
        def _save(e):
            update_setting("gemini_api_key", gemini_key.value)
            update_setting("ss_api_key", ss_key.value)
            self.settings = get_settings()
            self._snack("설정 저장 완료")
            
        self.settings_col.controls.extend([
            gemini_key,
            ss_key,
            ft.Button("저장", on_click=_save)
        ])
    
    def _prompt_gemini_key_if_missing(self):
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY and not self.settings.get("gemini_api_key"):
            self.rail.selected_index = 4
            self.content_area.content = self.view_settings
            self.page.update()
            self._snack("Gemini API 키를 먼저 설정해주세요.", bgcolor=ft.Colors.RED)

    def _on_ref_toggle(self, e):
        update_setting("enable_references", e.control.value)
        self.settings = get_settings()

    def _snack(self, msg, bgcolor=ft.Colors.BLACK87):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=bgcolor)
        self.page.snack_bar.open = True
        self.page.update()
    
    def _copy(self, text):
        pyperclip.copy(text)
        self._snack("복사되었습니다")


def main(page: ft.Page):
    # Font setup if needed
    page.fonts = {
        "Pretendard": "https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css"
    }
    page.theme = ft.Theme(font_family="Pretendard")
    App(page)

if __name__ == "__main__":
    ft.run(main)
