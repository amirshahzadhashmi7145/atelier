from app.domain.test_integrity import weakened_tests


def test_deleting_a_test_file_is_rejected():
    diff = """\
diff --git a/tests/test_app.py b/tests/test_app.py
deleted file mode 100644
--- a/tests/test_app.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def test_ok():
-    assert True
"""
    assert weakened_tests(diff) == ["Deleted test file 'tests/test_app.py'."]


def test_removing_an_assertion_is_rejected():
    diff = """\
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,3 +1,2 @@
 def test_ok():
-    assert response.status_code == 401
     return True
"""
    assert any("assertion" in item for item in weakened_tests(diff))


def test_skipping_a_test_is_rejected():
    diff = """\
diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,2 +1,3 @@
+@pytest.mark.skip(reason="later")
 def test_ok():
     assert True
"""
    assert any("skipped" in item for item in weakened_tests(diff))


def test_implementation_edits_are_allowed():
    diff = """\
diff --git a/server/app.py b/server/app.py
--- a/server/app.py
+++ b/server/app.py
@@ -1,2 +1,2 @@
-def create_record():
+def create_record() -> dict:
     return {"id": "1"}
"""
    assert weakened_tests(diff) == []
