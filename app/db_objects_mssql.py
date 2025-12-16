from sqlalchemy import text
from app.extensions import db

TRIGGER_SQL = r"""
IF OBJECT_ID(N'dbo.trg_books_stock_guard', N'TR') IS NULL
BEGIN
    EXEC('
    CREATE TRIGGER dbo.trg_books_stock_guard
    ON dbo.books
    AFTER INSERT, UPDATE
    AS
    BEGIN
        SET NOCOUNT ON;

        UPDATE b
        SET
            b.available_copies =
                CASE
                    WHEN b.available_copies < 0 THEN 0
                    WHEN b.available_copies > b.total_copies THEN b.total_copies
                    ELSE b.available_copies
                END
        FROM dbo.books b
        INNER JOIN inserted i ON i.id = b.id;
    END
    ')
END
"""

SP_BORROW_SQL = r"""
IF OBJECT_ID(N'dbo.sp_borrow_book', N'P') IS NULL
BEGIN
    EXEC('
    CREATE PROCEDURE dbo.sp_borrow_book
        @user_id INT,
        @book_id INT,
        @days INT = 14
    AS
    BEGIN
        SET NOCOUNT ON;

        BEGIN TRY
            BEGIN TRAN;

            DECLARE @available INT;

            SELECT @available = available_copies
            FROM dbo.books WITH (UPDLOCK, ROWLOCK)
            WHERE id = @book_id;

            IF @available IS NULL
            BEGIN
                RAISERROR(''Kitap bulunamadı'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            IF @available < 1
            BEGIN
                RAISERROR(''Kitap mevcut değil'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            UPDATE dbo.books
            SET available_copies = available_copies - 1
            WHERE id = @book_id;

            DECLARE @due_date DATETIME2 = DATEADD(DAY, @days, SYSUTCDATETIME());

            INSERT INTO dbo.borrows (user_id, book_id, due_date, status, borrowed_at)
            VALUES (@user_id, @book_id, @due_date, ''active'', SYSUTCDATETIME());

            DECLARE @borrow_id INT = SCOPE_IDENTITY();

            COMMIT TRAN;

            SELECT @borrow_id AS borrow_id, @due_date AS due_date;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN;
            DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
            RAISERROR(@msg, 16, 1);
        END CATCH
    END
    ')
END
ELSE
BEGIN
    EXEC('
    ALTER PROCEDURE dbo.sp_borrow_book
        @user_id INT,
        @book_id INT,
        @days INT = 14
    AS
    BEGIN
        SET NOCOUNT ON;

        BEGIN TRY
            BEGIN TRAN;

            DECLARE @available INT;

            SELECT @available = available_copies
            FROM dbo.books WITH (UPDLOCK, ROWLOCK)
            WHERE id = @book_id;

            IF @available IS NULL
            BEGIN
                RAISERROR(''Kitap bulunamadı'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            IF @available < 1
            BEGIN
                RAISERROR(''Kitap mevcut değil'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            UPDATE dbo.books
            SET available_copies = available_copies - 1
            WHERE id = @book_id;

            DECLARE @due_date DATETIME2 = DATEADD(DAY, @days, SYSUTCDATETIME());

            INSERT INTO dbo.borrows (user_id, book_id, due_date, status, borrowed_at)
            VALUES (@user_id, @book_id, @due_date, ''active'', SYSUTCDATETIME());

            DECLARE @borrow_id INT = SCOPE_IDENTITY();

            COMMIT TRAN;

            SELECT @borrow_id AS borrow_id, @due_date AS due_date;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN;
            DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
            RAISERROR(@msg, 16, 1);
        END CATCH
    END
    ')
END
"""

# ✅ RETURN SP: user kontrolü + iade + stok artırma atomik
SP_RETURN_SQL = r"""
IF OBJECT_ID(N'dbo.sp_return_book', N'P') IS NULL
BEGIN
    EXEC('
    CREATE PROCEDURE dbo.sp_return_book
        @borrow_id INT,
        @user_id INT
    AS
    BEGIN
        SET NOCOUNT ON;

        BEGIN TRY
            BEGIN TRAN;

            DECLARE @book_id INT;
            DECLARE @returned_at DATETIME2;
            DECLARE @already_returned DATETIME2;

            -- Borrow kaydını kilitle
            SELECT
                @book_id = book_id,
                @already_returned = returned_at
            FROM dbo.borrows WITH (UPDLOCK, ROWLOCK)
            WHERE id = @borrow_id AND user_id = @user_id;

            IF @book_id IS NULL
            BEGIN
                RAISERROR(''Ödünç kaydı bulunamadı (ya da sana ait değil)'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            IF @already_returned IS NOT NULL
            BEGIN
                RAISERROR(''Zaten iade edilmiş'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            SET @returned_at = SYSUTCDATETIME();

            UPDATE dbo.borrows
            SET returned_at = @returned_at,
                status = ''returned''
            WHERE id = @borrow_id AND user_id = @user_id;

            -- Stok artır (total sınırını trigger ayrıca koruyor)
            UPDATE dbo.books
            SET available_copies = available_copies + 1
            WHERE id = @book_id;

            COMMIT TRAN;

            SELECT @returned_at AS returned_at;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN;
            DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
            RAISERROR(@msg, 16, 1);
        END CATCH
    END
    ')
END
ELSE
BEGIN
    EXEC('
    ALTER PROCEDURE dbo.sp_return_book
        @borrow_id INT,
        @user_id INT
    AS
    BEGIN
        SET NOCOUNT ON;

        BEGIN TRY
            BEGIN TRAN;

            DECLARE @book_id INT;
            DECLARE @returned_at DATETIME2;
            DECLARE @already_returned DATETIME2;

            SELECT
                @book_id = book_id,
                @already_returned = returned_at
            FROM dbo.borrows WITH (UPDLOCK, ROWLOCK)
            WHERE id = @borrow_id AND user_id = @user_id;

            IF @book_id IS NULL
            BEGIN
                RAISERROR(''Ödünç kaydı bulunamadı (ya da sana ait değil)'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            IF @already_returned IS NOT NULL
            BEGIN
                RAISERROR(''Zaten iade edilmiş'', 16, 1);
                ROLLBACK TRAN;
                RETURN;
            END

            SET @returned_at = SYSUTCDATETIME();

            UPDATE dbo.borrows
            SET returned_at = @returned_at,
                status = ''returned''
            WHERE id = @borrow_id AND user_id = @user_id;

            UPDATE dbo.books
            SET available_copies = available_copies + 1
            WHERE id = @book_id;

            COMMIT TRAN;

            SELECT @returned_at AS returned_at;
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN;
            DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
            RAISERROR(@msg, 16, 1);
        END CATCH
    END
    ')
END
"""

def ensure_db_objects_mssql(app):
    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()
        try:
            conn.execute(text(TRIGGER_SQL))
            conn.execute(text(SP_BORROW_SQL))
            conn.execute(text(SP_RETURN_SQL))
            trans.commit()
            app.logger.info("[db_objects_mssql] Trigger + SP'ler ensure edildi (borrow+return).")
        except Exception as e:
            trans.rollback()
            app.logger.error(f"[db_objects_mssql] HATA: {e}")
            raise
        finally:
            conn.close()
