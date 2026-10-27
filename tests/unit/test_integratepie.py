"""Tests para IntegratePIE connector — work items, publisher, knowledge base."""


from jarvis.integrations.azure_devops import AzureDevOpsExtended, _strip_html


class TestStripHTML:
    def test_basic(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty(self):
        assert _strip_html("") == ""
        assert _strip_html(None) == ""

    def test_nested(self):
        assert _strip_html("<div><ul><li>Item 1</li><li>Item 2</li></ul></div>") == "Item 1Item 2"

    def test_plain_text(self):
        assert _strip_html("no html here") == "no html here"


class TestAzureDevOpsExtended:
    def test_not_configured(self):
        client = AzureDevOpsExtended(org_url="", pat="", project="")
        assert client.is_configured is False

    def test_configured(self):
        client = AzureDevOpsExtended(org_url="https://dev.azure.com/org", pat="fake", project="proj")
        assert client.is_configured is True

    def test_get_work_item_not_configured(self):
        client = AzureDevOpsExtended(org_url="", pat="", project="")
        assert client.get_work_item(123) is None

    def test_get_pr_work_items_not_configured(self):
        client = AzureDevOpsExtended(org_url="", pat="", project="")
        assert client.get_pr_work_items(456) == []

    def test_parse_work_item(self):
        client = AzureDevOpsExtended(org_url="https://dev.azure.com/org", pat="x", project="p")
        data = {
            "id": 100,
            "fields": {
                "System.Title": "Test PBI",
                "System.WorkItemType": "Product Backlog Item",
                "System.State": "Active",
                "System.Description": "<p>Test desc</p>",
                "Microsoft.VSTS.Common.AcceptanceCriteria": "<ul><li>AC 1</li><li>AC 2</li></ul>",
                "System.AssignedTo": {"displayName": "Juan"},
                "System.Tags": "frontend;urgent",
            },
            "relations": [
                {
                    "attributes": {"name": "Parent"},
                    "url": "https://dev.azure.com/_apis/wit/workItems/50",
                },
                {
                    "attributes": {"name": "Child"},
                    "url": "https://dev.azure.com/_apis/wit/workItems/101",
                },
                {
                    "attributes": {"name": "Child"},
                    "url": "https://dev.azure.com/_apis/wit/workItems/102",
                },
            ],
            "_links": {"html": {"href": "https://dev.azure.com/org/proj/_workitems/edit/100"}},
        }

        wi = client._parse_work_item(data)
        assert wi.id == 100
        assert wi.title == "Test PBI"
        assert wi.work_item_type == "Product Backlog Item"
        assert wi.state == "Active"
        assert wi.description == "Test desc"
        assert "AC 1" in wi.acceptance_criteria
        assert wi.assigned_to == "Juan"
        assert wi.tags == ["frontend", "urgent"]
        assert wi.parent_id == 50
        assert wi.children_ids == [101, 102]
        assert "100" in wi.url

    def test_prepare_comment(self):
        client = AzureDevOpsExtended(org_url="x", pat="x", project="x")
        prepared = client.prepare_comment(123, "## QA Report\nAll good.", ["report.md"])
        assert prepared["pr_id"] == 123
        assert prepared["status"] == "pending_approval"
        assert "QA Report" in prepared["preview"]
        assert "report.md" in prepared["evidence_paths"]


class TestPIEKnowledgeBase:
    def test_seed_knowledge(self, tmp_path):
        from jarvis.integrations.pie_knowledge import seed_knowledge
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        store = MemoryStore(db_path=str(tmp_path / "kb.db"))
        mgr = MemoryManager(store=store, embeddings_enabled=False)

        added = seed_knowledge(mgr)
        assert added == 15

        # Verificar que se pueden buscar
        results = mgr.search("FUR rollout", project="integratepie")
        assert len(results) >= 1
        assert any("FUR" in r[0].content for r in results)

        mgr.close()

    def test_seed_idempotent(self, tmp_path):
        from jarvis.integrations.pie_knowledge import seed_knowledge
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        store = MemoryStore(db_path=str(tmp_path / "kb2.db"))
        mgr = MemoryManager(store=store, embeddings_enabled=False)

        first = seed_knowledge(mgr)
        second = seed_knowledge(mgr)
        assert first == 15
        assert second == 0  # No duplicates

        assert mgr.count(project="integratepie") == 15
        mgr.close()

    def test_knowledge_isolated(self, tmp_path):
        from jarvis.integrations.pie_knowledge import seed_knowledge
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        store = MemoryStore(db_path=str(tmp_path / "kb3.db"))
        mgr = MemoryManager(store=store, embeddings_enabled=False)

        seed_knowledge(mgr)

        # IntegratePIE knowledge should not appear in kamecol searches
        kc_results = mgr.search("FUR rollout", project="kamecol")
        assert len(kc_results) == 0

        mgr.close()
