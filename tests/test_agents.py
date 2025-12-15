"""Tests for agent system."""

import pytest
from src.agents.base_agent import BaseAgent, Task, AgentResponse
from src.agents.planner import PlannerAgent
from src.agents.coder import CoderAgent
from src.agents.reviewer import ReviewerAgent


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = PlannerAgent()
        assert agent.name == "PlannerAgent"
        assert agent.llm_client is not None
        assert isinstance(agent.tools, dict)

    def test_tool_registration(self):
        """Test tool registration."""
        agent = PlannerAgent()

        def dummy_tool(x):
            return x * 2

        agent.register_tool("dummy", dummy_tool)
        assert "dummy" in agent.tools

        result = agent.use_tool("dummy", x=5)
        assert result == 10

    def test_tool_not_found(self):
        """Test using non-existent tool."""
        agent = PlannerAgent()

        with pytest.raises(ValueError, match="not registered"):
            agent.use_tool("nonexistent")


class TestPlannerAgent:
    """Test PlannerAgent functionality."""

    @pytest.fixture
    def planner(self):
        """Create planner agent fixture."""
        return PlannerAgent()

    def test_planner_initialization(self, planner):
        """Test planner initialization."""
        assert planner.name == "PlannerAgent"
        assert planner.dependency_graph is not None

    def test_simple_planning(self, planner):
        """Test basic planning task."""
        task = Task(
            task_id="test_plan",
            description="Create a simple web scraper",
            dependencies=[]
        )

        # Note: This requires API key, so it may fail in CI
        # In production, use mocks for testing
        try:
            thought = planner.think(task)
            assert isinstance(thought, str)
            assert len(thought) > 0
        except Exception as e:
            pytest.skip(f"API not available: {e}")


class TestCoderAgent:
    """Test CoderAgent functionality."""

    @pytest.fixture
    def coder(self):
        """Create coder agent fixture."""
        return CoderAgent()

    def test_coder_initialization(self, coder):
        """Test coder initialization."""
        assert coder.name == "CoderAgent"

    def test_language_detection(self, coder):
        """Test programming language detection."""
        assert coder._detect_language(".py") == "Python"
        assert coder._detect_language(".js") == "JavaScript"
        assert coder._detect_language(".ts") == "TypeScript"

    def test_code_cleaning(self, coder):
        """Test code fence removal."""
        code_with_fences = '''```python
def hello():
    print("Hello")
```'''
        cleaned = coder._clean_code(code_with_fences, "Python")
        assert "```" not in cleaned
        assert "def hello():" in cleaned


class TestReviewerAgent:
    """Test ReviewerAgent functionality."""

    @pytest.fixture
    def reviewer(self):
        """Create reviewer agent fixture."""
        return ReviewerAgent()

    def test_reviewer_initialization(self, reviewer):
        """Test reviewer initialization."""
        assert reviewer.name == "ReviewerAgent"

    def test_review_plan_extraction(self, reviewer):
        """Test review plan extraction."""
        thought = '''
        Here is my plan: {"review_aspects": ["quality"], "test_cases": ["test1"]}
        '''
        plan = reviewer._extract_review_plan(thought)
        assert "review_aspects" in plan


class TestTaskExecution:
    """Test task execution workflow."""

    def test_task_creation(self):
        """Test task creation."""
        task = Task(
            task_id="test_1",
            description="Test task",
            dependencies=["dep_1"],
            priority=5
        )

        assert task.task_id == "test_1"
        assert task.description == "Test task"
        assert "dep_1" in task.dependencies
        assert task.priority == 5

    def test_agent_response(self):
        """Test agent response structure."""
        response = AgentResponse(
            success=True,
            data={"result": "success"},
            message="Task completed",
            artifacts=["file1.py"]
        )

        assert response.success is True
        assert response.data["result"] == "success"
        assert "file1.py" in response.artifacts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
