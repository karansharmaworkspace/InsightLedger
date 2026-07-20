"""Knowledge Intelligence Dashboard page.

Provides interface for document ingestion, knowledge graph exploration,
maintenance analysis, and compliance status.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QSplitter,
    QFileDialog, QTabWidget,
    QLineEdit, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt
import os
import json


class KnowledgeIntelPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._platform = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel("Industrial Knowledge Intelligence")
        header.setStyleSheet("color: #fff; font-size: 22px; font-weight: bold;")
        layout.addWidget(header)

        subtitle = QLabel("Document ingestion, entity extraction, knowledge graph, maintenance & compliance")
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(subtitle)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #1e1e1e; }
            QTabBar::tab { background: #2d2d2d; color: #aaa; padding: 8px 16px; }
            QTabBar::tab:selected { background: #0078d4; color: #fff; }
        """)

        # Tab 1: Document Ingestion
        self.tabs.addTab(self._create_ingestion_tab(), "Documents")

        # Tab 2: Knowledge Graph
        self.tabs.addTab(self._create_kg_tab(), "Knowledge Graph")

        # Tab 3: Maintenance Intelligence
        self.tabs.addTab(self._create_maintenance_tab(), "Maintenance")

        # Tab 4: Compliance
        self.tabs.addTab(self._create_compliance_tab(), "Compliance")

        # Tab 5: Visualizations
        self.tabs.addTab(self._create_visualizations_tab(), "Visualizations")

        layout.addWidget(self.tabs)

    def _create_ingestion_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Ingestion controls
        controls = QHBoxLayout()
        self.ingest_file_btn = QPushButton("Ingest File")
        self.ingest_file_btn.clicked.connect(self._ingest_file)
        controls.addWidget(self.ingest_file_btn)

        self.ingest_dir_btn = QPushButton("Ingest Directory")
        self.ingest_dir_btn.clicked.connect(self._ingest_dir)
        controls.addWidget(self.ingest_dir_btn)

        controls.addStretch()

        self.ingest_status = QLabel("No documents ingested")
        self.ingest_status.setStyleSheet("color: #888;")
        controls.addWidget(self.ingest_status)

        layout.addLayout(controls)

        # Progress
        self.ingest_progress = QProgressBar()
        self.ingest_progress.setVisible(False)
        layout.addWidget(self.ingest_progress)

        # Document list
        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderLabels(["Document", "Type", "Chunks", "Entities"])
        self.doc_tree.setStyleSheet("""
            QTreeWidget { background: #1a1a2e; color: #ccc; border: 1px solid #333;
                          font-size: 12px; }
            QTreeWidget::item:hover { background: #16213e; }
        """)
        layout.addWidget(self.doc_tree)

        # Stats
        self.doc_stats = QLabel("")
        self.doc_stats.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.doc_stats)

        return tab

    def _create_kg_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Search
        search_layout = QHBoxLayout()
        self.kg_search = QLineEdit()
        self.kg_search.setPlaceholderText("Search entities (e.g., V-101, ISO 9001)...")
        self.kg_search.returnPressed.connect(self._search_kg)
        search_layout.addWidget(self.kg_search)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._search_kg)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Splitter: tree + details
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.kg_tree = QTreeWidget()
        self.kg_tree.setHeaderLabel("Entities")
        self.kg_tree.setStyleSheet("""
            QTreeWidget { background: #1a1a2e; color: #ccc; border: 1px solid #333; }
        """)
        self.kg_tree.itemClicked.connect(self._on_entity_click)
        splitter.addWidget(self.kg_tree)

        self.kg_detail = QTextEdit()
        self.kg_detail.setReadOnly(True)
        self.kg_detail.setStyleSheet("""
            QTextEdit { background: #0f3460; color: #e0e0e0; border: 1px solid #333;
                        padding: 12px; font-size: 12px; }
        """)
        splitter.addWidget(self.kg_detail)

        splitter.setSizes([300, 500])
        layout.addWidget(splitter)

        # Stats
        self.kg_stats = QLabel("")
        self.kg_stats.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(self.kg_stats)

        return tab

    def _create_maintenance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Equipment search
        search_layout = QHBoxLayout()
        self.maint_search = QLineEdit()
        self.maint_search.setPlaceholderText("Equipment tag (e.g., V-101, P-202A)...")
        search_layout.addWidget(self.maint_search)

        analyze_btn = QPushButton("Analyze")
        analyze_btn.clicked.connect(self._analyze_maintenance)
        search_layout.addWidget(analyze_btn)
        layout.addLayout(search_layout)

        # Results
        self.maint_results = QTextEdit()
        self.maint_results.setReadOnly(True)
        self.maint_results.setStyleSheet("""
            QTextEdit { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333;
                        padding: 12px; font-size: 12px; }
        """)
        layout.addWidget(self.maint_results)

        return tab

    def _create_compliance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls
        controls = QHBoxLayout()
        check_btn = QPushButton("Check Compliance Status")
        check_btn.clicked.connect(self._check_compliance)
        controls.addWidget(check_btn)

        audit_btn = QPushButton("Generate Audit Package")
        audit_btn.clicked.connect(self._generate_audit)
        controls.addWidget(audit_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Results
        self.compliance_results = QTextEdit()
        self.compliance_results.setReadOnly(True)
        self.compliance_results.setStyleSheet("""
            QTextEdit { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333;
                        padding: 12px; font-size: 12px; }
        """)
        layout.addWidget(self.compliance_results)

        return tab

    def _create_visualizations_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Visualization buttons
        controls = QHBoxLayout()

        kg_viz_btn = QPushButton("Generate Knowledge Graph")
        kg_viz_btn.clicked.connect(self._generate_kg_visualization)
        controls.addWidget(kg_viz_btn)

        crossref_btn = QPushButton("Generate Cross-Reference Matrix")
        crossref_btn.clicked.connect(self._generate_crossref)
        controls.addWidget(crossref_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Results
        self.viz_results = QTextEdit()
        self.viz_results.setReadOnly(True)
        self.viz_results.setStyleSheet("""
            QTextEdit { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333;
                        padding: 12px; font-size: 12px; }
        """)
        layout.addWidget(self.viz_results)

        return tab

    def _get_platform(self):
        if self._platform is None:
            try:
                from core.knowledge_platform import KnowledgePlatform
                self._platform = KnowledgePlatform()
            except Exception as e:
                print(f"[KnowledgeIntel] Platform init error: {e}")
        return self._platform

    def _ingest_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "",
            "All Supported (*.pdf *.xlsx *.xls *.png *.jpg *.jpeg *.txt *.md *.csv);;PDF Files (*.pdf);;Excel (*.xlsx *.xls);;Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self._run_ingestion(file_path, single=True)

    def _ingest_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self._run_ingestion(dir_path, single=False)

    def _run_ingestion(self, path: str, single: bool = True):
        platform = self._get_platform()
        if not platform:
            self.ingest_status.setText("Platform not initialized")
            return

        self.ingest_progress.setVisible(True)
        self.ingest_progress.setRange(0, 0)  # Indeterminate

        try:
            if single:
                result = platform.ingest_document(path)
            else:
                result = platform.ingest_directory(path)

            self.ingest_progress.setVisible(False)
            if result["status"] == "success":
                self.ingest_status.setText(f"Ingested: {result.get('chunks', result.get('total_chunks', 0))} chunks")
                self._refresh_doc_tree()
            else:
                self.ingest_status.setText(f"Error: {result.get('message', 'Unknown error')}")
        except Exception as e:
            self.ingest_progress.setVisible(False)
            self.ingest_status.setText(f"Error: {e}")

    def _refresh_doc_tree(self):
        platform = self._get_platform()
        if not platform:
            return

        self.doc_tree.clear()
        kg_stats = platform.get_knowledge_graph_stats()
        rag_stats = platform.get_rag_stats()

        source_docs: dict[str, list] = {}
        for nid, node in platform.kg.nodes.items():
            for src in node.get("sources", []):
                if src not in source_docs:
                    source_docs[src] = []
                source_docs[src].append(node)

        for doc_name, nodes in sorted(source_docs.items()):
            doc_item = QTreeWidgetItem(self.doc_tree)
            doc_item.setText(0, doc_name)
            doc_item.setText(1, "Document")
            doc_item.setText(2, str(len(nodes)))
            for node in nodes:
                child = QTreeWidgetItem(doc_item)
                child.setText(0, node["value"])
                child.setText(1, node["type"])
                child.setText(2, "")
                child.setText(3, f"{node.get('confidence', 0):.0%}")

        self.doc_stats.setText(
            f"Knowledge Graph: {kg_stats['total_nodes']} nodes, {kg_stats['total_edges']} edges | "
            f"Embeddings: {rag_stats['total_chunks']} chunks"
        )

    def _search_kg(self):
        platform = self._get_platform()
        if not platform:
            return

        query = self.kg_search.text().strip()
        if not query:
            return

        self.kg_tree.clear()

        # Search by value
        results = platform.kg.find_by_value(query)
        if not results:
            # Try by type
            results = platform.kg.find_by_type(query)

        for entity in results:
            item = QTreeWidgetItem(self.kg_tree)
            item.setText(0, f"{entity['value']}")
            item.setText(1, entity['type'])
            item.setData(0, Qt.ItemDataRole.UserRole, entity)

        self.kg_stats.setText(f"Found {len(results)} entities")

    def _on_entity_click(self, item, col):
        entity = item.data(0, Qt.ItemDataRole.UserRole)
        if not entity:
            return

        platform = self._get_platform()
        if not platform:
            return

        # Get network
        network = platform.kg.get_entity_network(entity["value"], depth=1)

        detail = f"<b>{entity['value']}</b> ({entity['type']})<br>"
        detail += f"<b>Sources:</b> {', '.join(entity.get('sources', []))}<br>"
        detail += f"<b>Confidence:</b> {entity.get('confidence', 0):.0%}<br><br>"

        if network["edges"]:
            detail += "<b>Connected entities:</b><br>"
            for edge in network["edges"]:
                other_id = edge["target"] if edge["source"] == entity["id"] else edge["source"]
                if other_id in network["nodes"]:
                    other = network["nodes"][other_id]
                    detail += f"  {edge['relation']} → {other['value']} ({other['type']})<br>"

        self.kg_detail.setText(detail)

    def _analyze_maintenance(self):
        platform = self._get_platform()
        if not platform:
            return

        tag = self.maint_search.text().strip()
        if not tag:
            return

        analysis = platform.get_maintenance_analysis(tag)
        result = f"<b>Maintenance Analysis: {tag}</b><br><br>"
        result += f"<b>History Records:</b> {len(analysis['history'])}<br><br>"

        if analysis["recommendations"]:
            result += "<b>Recommendations:</b><br>"
            for rec in analysis["recommendations"]:
                result += f"  • {rec}<br>"

        self.maint_results.setText(result)

    def _check_compliance(self):
        platform = self._get_platform()
        if not platform:
            return

        status = platform.get_compliance_status()
        result = f"<b>Compliance Status</b><br><br>"
        result += f"<b>Documents Analyzed:</b> {status['total_documents']}<br>"
        result += f"<b>Total Gaps:</b> {status['total_gaps']}<br>"
        result += f"<b>Status:</b> {status['compliance_status']}<br><br>"

        if status["regulation_coverage"]:
            result += "<b>Regulation Coverage:</b><br>"
            for reg, count in status["regulation_coverage"].items():
                result += f"  • {reg}: {count} documents<br>"

        self.compliance_results.setText(result)

    def _generate_audit(self):
        platform = self._get_platform()
        if not platform:
            return

        package = platform.get_audit_package()
        result = f"<b>Compliance Audit Package</b><br><br>"
        result += f"<b>Audit Date:</b> {package['audit_date']}<br>"
        result += f"<b>Documents Reviewed:</b> {package['total_documents_reviewed']}<br>"
        result += f"<b>Status:</b> {package['compliance_status']}<br><br>"

        if package.get("recommendations"):
            result += "<b>Recommendations:</b><br>"
            for rec in package["recommendations"]:
                result += f"  • {rec}<br>"

        self.compliance_results.setText(result)

    def _generate_kg_visualization(self):
        platform = self._get_platform()
        if not platform:
            return

        try:
            from core.kg_visualizer import KGVisualizer
            viz = KGVisualizer()
            output_path = os.path.join(os.getcwd(), "knowledge_graph.html")
            viz.generate_graph_html(
                {"nodes": platform.kg.nodes, "edges": platform.kg.edges},
                output_path,
            )
            self.viz_results.setText(
                f"<b>Knowledge Graph Generated</b><br><br>"
                f"Saved to: {output_path}<br><br>"
                f"Open in browser to explore the interactive graph.<br>"
                f"Nodes: {len(platform.kg.nodes)}<br>"
                f"Edges: {len(platform.kg.edges)}"
            )
        except Exception as e:
            self.viz_results.setText(f"Error: {e}")

    def _generate_crossref(self):
        platform = self._get_platform()
        if not platform:
            return

        try:
            from core.crossref_visualizer import CrossRefVisualizer
            viz = CrossRefVisualizer()

            # Get all chunks from storage
            chunks = []
            storage_dir = os.path.join(os.getcwd(), "storage", "documents")
            if os.path.exists(storage_dir):
                for f in os.listdir(storage_dir):
                    if f.endswith(".json"):
                        with open(os.path.join(storage_dir, f)) as fh:
                            chunk_data = json.load(fh)
                            chunks.append(chunk_data)

            if not chunks:
                self.viz_results.setText("No documents ingested yet.")
                return

            matrix = viz.build_matrix(chunks)
            output_path = os.path.join(os.getcwd(), "crossref_matrix.html")
            viz.generate_html(matrix, output_path)

            shared = sum(1 for j in range(len(matrix.entities))
                        if sum(1 for i in range(len(matrix.documents)) if matrix.matrix[i][j]) >= 2)

            self.viz_results.setText(
                f"<b>Cross-Reference Matrix Generated</b><br><br>"
                f"Saved to: {output_path}<br><br>"
                f"Documents: {len(matrix.documents)}<br>"
                f"Entities: {len(matrix.entities)}<br>"
                f"Shared entities: {shared}"
            )
        except Exception as e:
            self.viz_results.setText(f"Error: {e}")
