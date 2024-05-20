
def disable_repeated_backup():
    import storage.cache as storage_cache
    from apps import base

    storage_cache.delete(storage_cache.APP_RECOVERY_REPEATED_BACKUP_UNLOCKED)
    base.remove_repeated_backup_filter()
