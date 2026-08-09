//! Live exchange rates from open.er-api.com, cached for half an hour per base
//! currency so a sheet full of conversions makes at most one request.

use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use crate::core::calculator::CurrencyConverter;

const API_TEMPLATE: &str = "https://open.er-api.com/v6/latest/";
const CACHE_DURATION: Duration = Duration::from_secs(1800);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(5);

struct CacheItem {
    loaded_at: Instant,
    rates: HashMap<String, f64>,
}

#[derive(Default)]
pub struct OpenExchangeRateCurrencyConverter {
    cache: Mutex<HashMap<String, CacheItem>>,
}

impl OpenExchangeRateCurrencyConverter {
    pub fn new() -> Self {
        Self::default()
    }

    fn rates(&self, base_currency: &str) -> Result<HashMap<String, f64>, String> {
        if let Some(cached) = self
            .cache
            .lock()
            .map_err(|_| "Currency cache is poisoned".to_string())?
            .get(base_currency)
        {
            if cached.loaded_at.elapsed() < CACHE_DURATION {
                return Ok(cached.rates.clone());
            }
        }

        let rates = fetch_rates(base_currency)?;
        if let Ok(mut cache) = self.cache.lock() {
            cache.insert(
                base_currency.to_string(),
                CacheItem {
                    loaded_at: Instant::now(),
                    rates: rates.clone(),
                },
            );
        }
        Ok(rates)
    }
}

fn fetch_rates(base_currency: &str) -> Result<HashMap<String, f64>, String> {
    let response: serde_json::Value = ureq::get(&format!("{API_TEMPLATE}{base_currency}"))
        .timeout(REQUEST_TIMEOUT)
        .call()
        .map_err(|error| format!("Currency lookup failed: {error}"))?
        .into_json()
        .map_err(|error| format!("Currency API returned invalid data: {error}"))?;

    if response.get("result").and_then(|value| value.as_str()) != Some("success") {
        return Err("Currency API request failed".to_string());
    }

    let raw = response
        .get("rates")
        .and_then(|value| value.as_object())
        .ok_or_else(|| "Currency API returned invalid data".to_string())?;

    Ok(raw
        .iter()
        .filter_map(|(code, rate)| Some((code.to_ascii_uppercase(), rate.as_f64()?)))
        .collect())
}

impl CurrencyConverter for OpenExchangeRateCurrencyConverter {
    fn convert(&self, amount: f64, from_currency: &str, to_currency: &str) -> Result<f64, String> {
        let source = from_currency.to_ascii_uppercase();
        let target = to_currency.to_ascii_uppercase();
        if source == target {
            return Ok(amount);
        }

        let rates = self.rates(&source)?;
        let rate = rates
            .get(&target)
            .ok_or_else(|| format!("Currency code not supported: {target}"))?;
        Ok(amount * rate)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identical_currencies_skip_the_network() {
        let converter = OpenExchangeRateCurrencyConverter::new();
        assert_eq!(converter.convert(25.0, "usd", "USD").unwrap(), 25.0);
        assert_eq!(converter.convert(25.0, "EUR", "eur").unwrap(), 25.0);
        assert!(converter.cache.lock().unwrap().is_empty());
    }

    #[test]
    fn cached_rates_are_used_without_refetching() {
        let converter = OpenExchangeRateCurrencyConverter::new();
        converter.cache.lock().unwrap().insert(
            "USD".to_string(),
            CacheItem {
                loaded_at: Instant::now(),
                rates: HashMap::from([("EUR".to_string(), 0.92)]),
            },
        );
        assert!((converter.convert(100.0, "usd", "eur").unwrap() - 92.0).abs() < 1e-9);
    }

    #[test]
    fn unknown_target_currencies_are_reported() {
        let converter = OpenExchangeRateCurrencyConverter::new();
        converter.cache.lock().unwrap().insert(
            "USD".to_string(),
            CacheItem {
                loaded_at: Instant::now(),
                rates: HashMap::from([("EUR".to_string(), 0.92)]),
            },
        );
        let error = converter.convert(1.0, "usd", "zzz").unwrap_err();
        assert!(error.contains("not supported"));
    }
}
