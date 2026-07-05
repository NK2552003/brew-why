import asyncio
from typing import List, Dict

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Input, Markdown, Button
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual import on, work

from brew_why import core
from brew_why import display

class PackageDetailScreen(ModalScreen):
    """A modal screen that displays details for a single package."""
    
    DEFAULT_CSS = '''
    PackageDetailScreen {
        align: center middle;
    }
    
    #detail-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #close-btn {
        margin-top: 1;
        width: 100%;
    }
    '''
    
    def __init__(self, pkg: Dict, **kwargs):
        super().__init__(**kwargs)
        self.pkg = pkg
        
    def compose(self) -> ComposeResult:
        name = self.pkg.get('name', 'Unknown')
        version = self.pkg.get('version', 'Unknown')
        size_str = display.format_size(self.pkg.get('size', 0))
        deps = self.pkg.get('deps', [])
        uses = self.pkg.get('uses', [])
        ptype = self.pkg.get('_category', 'Unknown')
        
        md_content = f"# {name} v{version}\n\n"
        md_content += f"**Type:** {ptype} | **Size:** {size_str}\n\n"
        
        md_content += f"## Dependencies ({len(deps)})\n"
        md_content += ", ".join(deps) if deps else "None"
        md_content += "\n\n"
        
        md_content += f"## Used By ({len(uses)})\n"
        md_content += ", ".join(uses) if uses else "None"
        md_content += "\n\n"
        
        if ptype == "Orphan":
            md_content += "> **Safe to Remove:** This package is an orphaned dependency.\n"
        elif ptype == "User":
            md_content += "> **Top-Level:** You explicitly installed this package.\n"
        elif ptype == "Dep":
            md_content += "> **Required:** Other installed packages depend on this.\n"
            
        with Container(id="detail-container"):
            yield Markdown(md_content)
            yield Button("Close", id="close-btn", variant="primary")
            
    @on(Button.Pressed, "#close-btn")
    def close_modal(self) -> None:
        self.app.pop_screen()


class Dashboard(Static):
    """The main dashboard view for the TUI."""
    
    DEFAULT_CSS = '''
    #search {
        margin-bottom: 1;
    }
    #filter-bar {
        height: 1;
        margin-bottom: 1;
    }
    .filter-btn {
        margin-right: 1;
        border: none;
        background: $surface;
        color: $text;
        min-width: 12;
        height: 1;
    }
    .filter-btn.-active {
        background: $primary;
        color: $background;
        border: none;
        text-style: bold;
    }
    '''
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_pkgs: List[Dict] = []
        self.sort_col = "Size"
        self.sort_reverse = True
        self.active_type_filter = "All"
        
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="Search packages by name or type...", id="search")
            with Horizontal(id="filter-bar"):
                yield Button("All", id="btn-all", classes="filter-btn -active")
                yield Button("User", id="btn-user", classes="filter-btn")
                yield Button("Dep", id="btn-dep", classes="filter-btn")
                yield Button("Orphan", id="btn-orphan", classes="filter-btn")
            yield DataTable(id="pkg-table")
        
    async def on_mount(self) -> None:
        table = self.query_one("#pkg-table", DataTable)
        table.add_columns("Package", "Version", "Type", "Size", "Outdated")
        table.cursor_type = "row"
        
        # Load data in background to not block UI thread
        self.run_worker(self.load_data(), thread=True)
        
    async def load_data(self) -> None:
        table = self.query_one("#pkg-table", DataTable)
        search_input = self.query_one("#search", Input)
        self.app.call_from_thread(lambda: setattr(search_input, 'disabled', True))
        
        try:
            users, deps, orphans = core.get_all_data()
            
            for u in users:
                u['_category'] = "User"
            for d in deps:
                d['_category'] = "Dep"
            for o in orphans:
                o['_category'] = "Orphan"
                
            self.all_pkgs = users + deps + orphans
            
            self.app.call_from_thread(self.update_table)
            self.app.call_from_thread(lambda: setattr(search_input, 'disabled', False))
            self.app.call_from_thread(search_input.focus)
            
        except Exception as e:
            self.app.call_from_thread(table.add_row, "Error loading data", "", str(e), "", "")

    def update_table(self) -> None:
        table = self.query_one("#pkg-table", DataTable)
        table.clear()
        
        search_query = self.query_one("#search", Input).value.lower()
        
        # Filter by search
        filtered_pkgs = [
            p for p in self.all_pkgs
            if search_query in p.get('name', '').lower() or search_query in p.get('_category', '').lower()
        ]
        
        # Filter by type button
        if self.active_type_filter != "All":
            filtered_pkgs = [p for p in filtered_pkgs if p.get('_category') == self.active_type_filter]
        
        # Sort
        if self.sort_col == "Package":
            filtered_pkgs.sort(key=lambda x: x.get('name', ''), reverse=self.sort_reverse)
        elif self.sort_col == "Version":
            filtered_pkgs.sort(key=lambda x: x.get('version', ''), reverse=self.sort_reverse)
        elif self.sort_col == "Type":
            filtered_pkgs.sort(key=lambda x: x.get('_category', ''), reverse=self.sort_reverse)
        elif self.sort_col == "Size":
            filtered_pkgs.sort(key=lambda x: x.get('size', 0), reverse=self.sort_reverse)
        elif self.sort_col == "Outdated":
            filtered_pkgs.sort(key=lambda x: str(x.get('outdated', False)), reverse=self.sort_reverse)
            
        # Add rows
        for p in filtered_pkgs:
            ptype = p.get('_category', 'Unknown')
            size_str = display.format_size(p.get('size', 0))
            outdated_str = "Yes" if p.get('outdated') else "No"
            
            table.add_row(p['name'], p['version'], ptype, size_str, outdated_str, key=p['name'])
            
    @on(Input.Changed, "#search")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.update_table()
        
    @on(Button.Pressed, ".filter-btn")
    def on_filter_btn_pressed(self, event: Button.Pressed) -> None:
        # Reset all buttons
        for btn in self.query(".filter-btn"):
            btn.remove_class("-active")
            
        # Set active button
        event.button.add_class("-active")
        
        # Update filter state
        btn_id = event.button.id
        if btn_id == "btn-all":
            self.active_type_filter = "All"
        elif btn_id == "btn-user":
            self.active_type_filter = "User"
        elif btn_id == "btn-dep":
            self.active_type_filter = "Dep"
        elif btn_id == "btn-orphan":
            self.active_type_filter = "Orphan"
            
        self.update_table()
        
    @on(DataTable.HeaderSelected, "#pkg-table")
    def on_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col_names = ["Package", "Version", "Type", "Size", "Outdated"]
        clicked_col = col_names[event.column_index]
        
        if self.sort_col == clicked_col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = clicked_col
            self.sort_reverse = False
            
        self.update_table()
        
    @on(DataTable.RowSelected, "#pkg-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        pkg_name = event.row_key.value
        
        pkg_data = next((p for p in self.all_pkgs if p.get('name') == pkg_name), None)
        if pkg_data:
            self.app.push_screen(PackageDetailScreen(pkg_data))


class BrewWhyApp(App):
    """A Textual App to manage Homebrew dependencies."""
    
    TITLE = "BrewWhy Dashboard (v1.0.4)"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(Dashboard())
        yield Footer()
        
    def action_refresh(self) -> None:
        """Action to clear cache and refresh data."""
        core.clear_cache()
        dash = self.query_one(Dashboard)
        dash.run_worker(dash.load_data(), thread=True)
