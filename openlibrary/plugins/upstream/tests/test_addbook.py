"""py.test tests for addbook"""
import web
from .. import addbook
from openlibrary import accounts
from openlibrary.mocks.mock_infobase import MockSite


def strip_nones(d):
    return {k: v for k, v in d.items() if v is not None}


def mock_user():
    return type(
        'MockUser',
        (object,),
        {
            'is_admin': lambda slf: False,
            'is_librarian': lambda slf: False,
            'is_usergroup_member': lambda slf, grp: False,
        },
    )()


class TestSaveBookHelper:
    def setup_method(self, method):
        web.ctx.site = MockSite()

    def test_authors(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        s = addbook.SaveBookHelper(None, None)

        def f(data):
            return strip_nones(s.process_work(web.storage(data)))

        assert f({}) == {}
        assert f({"authors": []}) == {}
        assert f({"authors": [{"type": "/type/author_role"}]}) == {}

    def test_editing_orphan_creates_work(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                }
            ]
        )
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "",
                "work--title": "Original Edition Title",
                "edition--title": "Original Edition Title",
            }
        )

        s = addbook.SaveBookHelper(None, edition)
        s.save(formdata)

        assert len(web.ctx.site.docs) == 2
        assert web.ctx.site.get("/works/OL1W") is not None
        assert web.ctx.site.get("/works/OL1W").title == "Original Edition Title"

    def test_never_create_an_orphan(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )
        edition = web.ctx.site.get("/books/OL1M")
        work = web.ctx.site.get("/works/OL1W")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Original Work Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)
        print(web.ctx.site.get("/books/OL1M").title)
        assert web.ctx.site.get("/books/OL1M").works[0].key == "/works/OL1W"

    def test_moving_orphan(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                }
            ]
        )
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "",
                "work--title": "Original Edition Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "/works/OL1W",
            }
        )

        s = addbook.SaveBookHelper(None, edition)
        s.save(formdata)

        assert len(web.ctx.site.docs) == 1
        assert web.ctx.site.get("/books/OL1M").works[0].key == "/works/OL1W"

    def test_moving_orphan_ignores_work_edits(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                },
            ]
        )
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "",
                "work--title": "Modified Work Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "/works/OL1W",
            }
        )

        s = addbook.SaveBookHelper(None, edition)
        s.save(formdata)

        assert web.ctx.site.get("/works/OL1W").title == "Original Work Title"

    def test_editing_work(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL1W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Modified Work Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "/works/OL1W",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert web.ctx.site.get("/works/OL1W").title == "Modified Work Title"
        assert web.ctx.site.get("/books/OL1M").title == "Original Edition Title"

    def test_editing_edition(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL1W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Original Work Title",
                "edition--title": "Modified Edition Title",
                "edition--works--0--key": "/works/OL1W",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert web.ctx.site.get("/works/OL1W").title == "Original Work Title"
        assert web.ctx.site.get("/books/OL1M").title == "Modified Edition Title"

    def test_editing_work_and_edition(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL1W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Modified Work Title",
                "edition--title": "Modified Edition Title",
                "edition--works--0--key": "/works/OL1W",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert web.ctx.site.get("/works/OL1W").title == "Modified Work Title"
        assert web.ctx.site.get("/books/OL1M").title == "Modified Edition Title"

    def test_moving_edition(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL1W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Original Work Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "/works/OL2W",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert web.ctx.site.get("/books/OL1M").works[0].key == "/works/OL2W"

    def test_moving_edition_ignores_changes_to_work(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL1W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL1W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL1W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL1W",
                "work--title": "Modified Work Title",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "/works/OL2W",  # Changing work
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert web.ctx.site.get("/works/OL1W").title == "Original Work Title"

    def test_moving_edition_to_new_work(self, monkeypatch):
        monkeypatch.setattr(accounts, "get_current_user", mock_user)

        web.ctx.site.save_many(
            [
                {
                    "type": {"key": "/type/work"},
                    "key": "/works/OL100W",
                    "title": "Original Work Title",
                },
                {
                    "type": {"key": "/type/edition"},
                    "key": "/books/OL1M",
                    "title": "Original Edition Title",
                    "works": [{"key": "/works/OL100W"}],
                },
            ]
        )

        work = web.ctx.site.get("/works/OL100W")
        edition = web.ctx.site.get("/books/OL1M")

        formdata = web.storage(
            {
                "work--key": "/works/OL100W",
                "work--title": "FOO BAR",
                "edition--title": "Original Edition Title",
                "edition--works--0--key": "__new__",
            }
        )

        s = addbook.SaveBookHelper(work, edition)
        s.save(formdata)

        assert len(web.ctx.site.docs) == 3
        # Should create new work with edition data
        assert web.ctx.site.get("/works/OL1W") is not None
        new_work = web.ctx.site.get("/books/OL1M").works[0]
        assert new_work.key == "/works/OL1W"
        assert new_work.title == "Original Edition Title"
        # Should ignore edits to work data
        assert web.ctx.site.get("/works/OL100W").title == "Original Work Title"
