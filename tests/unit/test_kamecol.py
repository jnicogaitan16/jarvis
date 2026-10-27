"""Tests para KameCol integration — clientes, agente, modelos."""


from jarvis.integrations.kamecol import (
    DashboardKPIs,
    KameColAdminClient,
    KameColPublicClient,
    OrderStatus,
    Product,
)


class TestModels:
    def test_product(self):
        p = Product(slug="camiseta-negra", name="Camiseta Negra", price=89900)
        assert p.slug == "camiseta-negra"
        assert p.price == 89900
        assert p.in_stock is True

    def test_product_with_discount(self):
        p = Product(slug="x", name="X", price=100000, discount_price=79900)
        assert p.discount_price == 79900

    def test_order_status(self):
        os = OrderStatus(reference="KC-001", status="PAID", total=150000)
        assert os.reference == "KC-001"
        assert os.status == "PAID"

    def test_dashboard_kpis(self):
        kpis = DashboardKPIs(revenue=5000000, orders_count=30, average_ticket=166666)
        assert kpis.revenue == 5000000


class TestPublicClient:
    def test_not_configured(self, monkeypatch):
        monkeypatch.delenv("KAMECOL_API_URL", raising=False)
        client = KameColPublicClient(base_url="")
        assert client.is_configured is False
        assert client.get_products() == []
        assert client.get_product_detail("x") is None
        assert client.get_order_status("ref") is None
        assert client.get_navigation() == []

    def test_configured(self):
        client = KameColPublicClient(base_url="https://example.com")
        assert client.is_configured is True

    def test_parse_product(self):
        client = KameColPublicClient(base_url="https://x.com")
        product = client._parse_product({
            "slug": "test-product",
            "name": "Test Product",
            "price": "99900",
            "discount_price": None,
            "category": {"name": "Camisetas"},
            "department": {"name": "Hombre"},
            "in_stock": True,
            "variants": [{"size": "M", "color": "Negro"}],
        })
        assert product.slug == "test-product"
        assert product.price == 99900
        assert product.category == "Camisetas"
        assert product.department == "Hombre"
        assert len(product.variants) == 1


class TestAdminClient:
    def test_not_configured(self):
        client = KameColAdminClient(base_url="", session_cookie="")
        assert client.is_configured is False
        assert client.get_dashboard() is None
        assert client.get_pending_recovery() == []
        assert client.send_reminder("x") is False
        assert client.get_inventory() == []

    def test_configured(self):
        client = KameColAdminClient(base_url="https://x.com", session_cookie="abc123")
        assert client.is_configured is True


class TestKameColAgent:
    def test_spec(self):
        from jarvis.agents.business.kamecol_agent import KameColAgent
        agent = KameColAgent()
        s = agent.spec()
        assert s.id == "biz.kamecol"
        assert "catalog" in s.skills
        assert "kamecol" in s.supported_projects

    def test_can_handle(self):
        from jarvis.agents.business.kamecol_agent import KameColAgent
        agent = KameColAgent()
        assert agent.can_handle("catalog", "kamecol") is True
        assert agent.can_handle("catalog", "integratepie") is False

    def test_detect_action_products(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.business.kamecol_agent import KameColAgent

        agent = KameColAgent()
        request = AgentRequest(
            intent="catalog",
            payload={"question": "buscar camiseta negra"},
            project="kamecol",
        )
        action = agent._detect_action(request)
        assert action == "search_products"

    def test_detect_action_order(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.business.kamecol_agent import KameColAgent

        agent = KameColAgent()
        request = AgentRequest(
            intent="",
            payload={"question": "estado del pedido KC-001"},
            project="kamecol",
        )
        action = agent._detect_action(request)
        assert action == "order_status"

    def test_detect_action_dashboard(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.business.kamecol_agent import KameColAgent

        agent = KameColAgent()
        request = AgentRequest(
            intent="",
            payload={"question": "métricas de ventas del dashboard"},
            project="kamecol",
        )
        action = agent._detect_action(request)
        assert action == "dashboard"

    def test_execute_without_config_returns_help(self):
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.business.kamecol_agent import KameColAgent

        agent = KameColAgent()
        request = AgentRequest(
            intent="",
            payload={"action": "help"},
            project="kamecol",
        )
        result = agent.execute(request)
        assert result.success is True
        assert "available_actions" in result.data

    def test_search_not_configured(self, monkeypatch):
        monkeypatch.delenv("KAMECOL_API_URL", raising=False)
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.business.kamecol_agent import KameColAgent

        agent = KameColAgent()
        request = AgentRequest(
            intent="catalog",
            payload={"action": "search_products", "search": "test"},
            project="kamecol",
        )
        result = agent.execute(request)
        # Sin KAMECOL_API_URL configurado, debería fallar informativamente
        assert result.success is False
        assert "KAMECOL_API_URL" in result.error
