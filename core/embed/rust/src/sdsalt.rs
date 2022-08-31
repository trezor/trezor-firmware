use crate::{
    storage::get_device_id,
    trezorhal::{
        fatfs::{close, mount, open, read, rename, unlink, unmount, FATFS, FIL},
        hmac::{hmac_sha256, SHA256_DIGEST_LENGTH},
        sdcard::{is_present, power_off, power_on},
        storage::ExternalSalt,
    },
    ui::model_tt::screens_fw::{insert_sd_card, retry_sd_card, retry_wrong_card},
};
use heapless::String;

pub enum LoadSDResult {
    Ok([u8; 32]),
    WrongSD,
    Error,
}

pub fn consteq(buf1: &[u8], buf2: &[u8]) -> bool {
    let mut diff: usize = buf1.len() - buf2.len();

    for i in 0..buf2.len() {
        diff |= (buf1[i] - buf2[i]) as usize;
    }

    diff == 0
}

pub fn load_salt(auth_key: &[u8], path: String<49>) -> Result<Option<[u8; 32]>, ()> {
    let mut fil: FIL = FIL::default();

    if let Ok(()) = open(&mut fil, path.as_str(), 1) {
        let mut salt = [0_u8; 32];
        let mut stored_tag = [0_u8; 16];

        if read(&mut fil, &mut salt).is_err() {
            return Err(());
        };
        if read(&mut fil, &mut stored_tag).is_err() {
            return Err(());
        };

        let mut result = [0_u8; SHA256_DIGEST_LENGTH as _];

        hmac_sha256(auth_key, &salt, &mut result);
        if close(&mut fil).is_err() {
            return Err(());
        };

        if consteq(&result[..16], &stored_tag) {
            return Ok(Some(salt));
        }
    }
    Ok(None)
}

pub fn load_sd_salt(key: &[u8]) -> LoadSDResult {
    let mut salt_path: String<49> = String::new();
    let mut new_salt_path: String<49> = String::new();

    let dev_id = get_device_id();

    unwrap!(salt_path.push_str("/trezor/device_"));
    unwrap!(salt_path.push_str(dev_id.as_str()));
    unwrap!(salt_path.push_str("/salt"));

    unwrap!(new_salt_path.push_str(salt_path.as_str()));
    unwrap!(new_salt_path.push_str(".new"));
    unwrap!(new_salt_path.push_str("\0"));
    unwrap!(salt_path.push_str("\0"));

    let mut ff: FATFS = FATFS::default();

    if mount(&mut ff).is_err() {
        return LoadSDResult::Error;
    };

    let salt = load_salt(key, salt_path.clone());

    if let Ok(salt) = salt {
        if let Some(salt) = salt {
            return LoadSDResult::Ok(salt);
        }
    } else {
        return LoadSDResult::Error;
    }

    let new_salt = load_salt(key, new_salt_path.clone());
    if let Ok(new_salt) = new_salt {
        if new_salt.is_none() {
            return LoadSDResult::WrongSD;
        }
    } else {
        return LoadSDResult::Error;
    }

    // Normal salt file does not exist, but new salt file exists. That means that
    // SD salt regeneration was interrupted earlier. Bring into consistent state.
    // TODO Possibly overwrite salt file with random data.
    if unlink(salt_path.as_str()).is_err() {
        return LoadSDResult::Error;
    };

    // fatfs rename can fail with a write error, which falls through as an
    // FatFSError.  This should be handled in calling code, by allowing the user
    // to retry.
    if rename(new_salt_path.as_str(), salt_path.as_str()).is_err() {
        return LoadSDResult::Error;
    };

    LoadSDResult::Error
}

pub fn load_sd_salt_wrapper(key: &[u8]) -> LoadSDResult {
    power_on();

    let result = load_sd_salt(key);

    let unmount_res = unmount();
    power_off();

    if unmount_res.is_err() {
        LoadSDResult::Error
    } else {
        result
    }
}

pub fn ensure_sdcard() -> bool {
    while !is_present() {
        let retry = insert_sd_card();
        if !retry {
            return false;
        }
    }
    true
}

pub fn sd_card(key: &[u8]) -> Option<ExternalSalt> {
    loop {
        if !ensure_sdcard() {
            return None;
        }

        let result = load_sd_salt_wrapper(key);

        match result {
            LoadSDResult::Ok(salt) => return Some(salt),
            LoadSDResult::WrongSD => {
                let retry = retry_wrong_card();
                if !retry {
                    return None;
                }
            }
            LoadSDResult::Error => {
                let retry = retry_sd_card();
                if !retry {
                    return None;
                }
            }
        }
    }
}
