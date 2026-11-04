import os, sqlite3, subprocess, sys
from pathlib import Path

def test_alembic_upgrade_on_clean_sqlite_database(tmp_path):
    backend=Path(__file__).resolve().parents[1]
    db_path=tmp_path/'clean.db'
    env=os.environ.copy(); env['DATABASE_URL']=f'sqlite:///{db_path.as_posix()}'
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=backend,env=env,check=True,capture_output=True,text=True)
    with sqlite3.connect(db_path) as connection:
        tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'review_jobs','ai_calls','check_cache','reports','embeddings','rule_examples'} <= tables
        revision_columns={row[1] for row in connection.execute('PRAGMA table_info(content_revisions)')}
        assert {'alt_text','is_ai_media','detected_language','image_analysis','locked_at','approved_snapshot'} <= revision_columns
        finding_columns={row[1] for row in connection.execute('PRAGMA table_info(claim_findings)')}
        assert 'state' in finding_columns
        assert len(tables)==21
