pub mod db_ops {

    use rocket::serde::{Deserialize, Serialize};
    use rocket::FromForm;
    use rocket_db_pools::sqlx::{pool::PoolConnection, Sqlite};
    use rocket_db_pools::{sqlx, Database};

    pub type Result<T, E = rocket::response::Debug<sqlx::Error>> = std::result::Result<T, E>;

    #[derive(Database)]
    #[database("search_Jan31_2023")]
    pub struct DBOpenAI(sqlx::SqlitePool);

    #[derive(Debug, Clone, Deserialize, Serialize)]
    #[serde(crate = "rocket::serde")]
    pub struct QueryItem {
        // #[serde(skip_deserializing, skip_serializing_if = "Option::is_none")]
        pub id: i64,
        pub category: String,
        pub note: String,
        pub input: String,
        pub template: String,
        pub choice_id: i64,
        pub choice: String,
        pub label: String,
        pub MI_label: String,
        pub to_search: String,
        pub total_count: Option<i64>,
        pub url: Option<String>,
    }

    #[derive(Debug, Clone, Deserialize, Serialize)]
    #[serde(crate = "rocket::serde", transparent)]
    pub struct ChoiceVec {
        pub choices: Vec<QueryItem>,
    }

    pub async fn load_data_all(db: &mut PoolConnection<Sqlite>) -> Vec<QueryItem> {
        let query_result: Vec<QueryItem> =
            sqlx::query_as!(QueryItem,
                r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
                FROM responses LEFT JOIN github ON responses.id=github.query_id 
                ORDER BY responses.id, responses.choice_id"#
            )
                .fetch_all(db)
                .await
                .unwrap();

        query_result
    }

    pub async fn load_data_by_id(db: &mut PoolConnection<Sqlite>, id: i64) -> Result<QueryItem> {
        sqlx::query_as!(QueryItem,
                r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
                FROM responses LEFT JOIN github ON responses.id=github.query_id 
                WHERE responses.id = ?"# , id)
            .fetch_one(db)
            .await
            .map_err(rocket::response::Debug)
    }

    pub async fn load_data_by_label(
        db: &mut PoolConnection<Sqlite>,
        label: &str,
    ) -> Vec<QueryItem> {
        let query_result: Vec<QueryItem> = sqlx::query_as!(
            QueryItem,
            r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
            FROM responses LEFT JOIN github ON responses.id=github.query_id 
            WHERE responses.label=? 
            ORDER BY responses.id, responses.choice_id"#,
            label
        )
        .fetch_all(db)
        .await
        .unwrap();

        query_result
    }

    pub async fn load_data_by_milabel(
        db: &mut PoolConnection<Sqlite>,
        label: &str,
    ) -> Vec<QueryItem> {
        let query_result: Vec<QueryItem> = sqlx::query_as!(
            QueryItem,
            r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
            FROM responses LEFT JOIN github ON responses.id=github.query_id 
            WHERE responses.MI_label=? 
            ORDER BY responses.id, responses.choice_id"#,
            label
        )
        .fetch_all(db)
        .await
        .unwrap();

        query_result
    }

    pub async fn load_data_to_look(
        db: &mut PoolConnection<Sqlite>,
    ) -> Vec<QueryItem> {
        let query_result: Vec<QueryItem> = sqlx::query_as!(
            QueryItem,
            r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
            FROM responses LEFT JOIN github ON responses.id=github.query_id 
            WHERE responses.MI_label="1" AND github.total_count<=100 AND github.total_count>0
            ORDER BY responses.id, responses.choice_id"#
        )
        .fetch_all(db)
        .await
        .unwrap();

        query_result
    }

    pub async fn load_data_to_look_label(
        db: &mut PoolConnection<Sqlite>,
        label: &str,
    ) -> Vec<QueryItem> {
        let query_result: Vec<QueryItem> = sqlx::query_as!(
            QueryItem,
            r#"SELECT responses.id,responses.category,responses.note,responses.input,responses.template,responses.choice_id,responses.choice,responses.label,responses.MI_label,responses.to_search,github.total_count as "total_count?",github.url as "url?"
            FROM responses LEFT JOIN github ON responses.id=github.query_id 
            WHERE responses.MI_label="1" AND responses.label=? AND github.total_count<=100 AND github.total_count>0
            ORDER BY responses.id, responses.choice_id"#,
            label
        )
        .fetch_all(db)
        .await
        .unwrap();

        query_result
    }
     
    #[derive(Debug, Clone, Deserialize, Serialize, FromForm)]
    #[serde(crate = "rocket::serde")]
    pub struct Item2Update {
        pub id: i64,
        pub to_search: String,
        pub label: String,
    }

    pub enum UpdateOpt {
        LabelOnly,
        ToSearchOnly,
        Both,
    }

    pub async fn update_data(
        db: &mut PoolConnection<Sqlite>,
        item: &Item2Update,
        update_option: UpdateOpt,
    ) -> Result<()> {
        match update_option {
            UpdateOpt::Both => {
                let _result = sqlx::query!(
                    "UPDATE responses SET label=?, to_search=? WHERE id=?",
                    item.label,
                    item.to_search,
                    item.id
                )
                .execute(db)
                .await
                .unwrap();
            }
            UpdateOpt::LabelOnly => {
                let _result = sqlx::query!(
                    "UPDATE responses SET label=? WHERE id=?",
                    item.label,
                    item.id
                )
                .execute(db)
                .await
                .unwrap();
            }
            UpdateOpt::ToSearchOnly => {
                let _result = sqlx::query!(
                    "UPDATE responses SET to_search=? WHERE id=?",
                    item.to_search,
                    item.id
                )
                .execute(db)
                .await
                .unwrap();
            }
        }

        Ok(())
    }

    #[derive(Debug, Clone, Deserialize, Serialize)]
    #[serde(crate = "rocket::serde")]
    pub struct GhItem {
        pub query_id: i64,
        pub total_count: i64,
        pub url: String,
    }

    pub async fn load_ghitem(db: &mut PoolConnection<Sqlite>, query_id: i64) -> Result<GhItem> {
        sqlx::query_as!(
            GhItem,
            "SELECT query_id, total_count, url FROM github where query_id = ?",
            query_id
        )
        .fetch_one(db)
        .await
        .map_err(rocket::response::Debug)
    }

    pub async fn update_ghitem(db: &mut PoolConnection<Sqlite>, item: &GhItem) -> Result<()> {
        let _result = sqlx::query!(
            "INSERT INTO github (query_id, total_count, url)
            VALUES (?, ?, ?)
            ON CONFLICT(query_id) DO UPDATE SET
            total_count=?,
            url=?
            WHERE query_id=?;",
            item.query_id,
            item.total_count,
            item.url,
            item.total_count,
            item.url,
            item.query_id
        )
        .execute(db)
        .await
        .unwrap();

        Ok(())
    }
}

pub mod gh_search {
    extern crate octocrab;

    use std::collections::HashSet;
    use std::thread;
    use std::time::{Duration, SystemTime, UNIX_EPOCH};

    use dotenv::dotenv;
    use octocrab::{models::Code, FromResponse, Page};
    use rocket::serde::{Deserialize, Serialize};
    use serde_json;
    use url::form_urlencoded::byte_serialize;

    #[derive(Debug, Clone, Deserialize, Serialize)]
    #[serde(crate = "rocket::serde")]
    pub struct GHRet {
        pub total_count: i64,
        pub url: String,
    }

    fn gh_search_preprocess(to_search: &str) -> Option<String> {
        let s: String = to_search
            .trim()
            .trim_start_matches("=")
            .trim()
            .trim_start_matches("\"")
            .trim()
            .trim_start_matches(".")
            .trim()
            // .trim_start_matches("[")
            // .trim()
            // .trim_start_matches("{")
            // .trim()
            .chars()
            .map(|c| match c {
                ',' => ' ',
                '@' => ' ',
                '"' => ' ',
                '&' => ' ',
                // '?' => ' ',
                ':' => ' ',
                // ']' => ' ',
                // '}' => ' ',
                _ => c,
            })
            .collect();
        if s.is_empty() || s == "#-#-#-#-#" {
            None
        } else {
            Some(s)
        }
    }

    fn gh_search_url(to_search: &str) -> String {
        let mut url = "https://github.com/search?q=".to_owned();
        if let Some(q) = gh_search_preprocess(to_search) {
            let params_encoded: String = byte_serialize(q.as_bytes()).collect();
            url.push_str(&params_encoded);
            url.push_str("&type=code");
            url
        } else {
            String::new()
        }
    }

    #[allow(dead_code)]
    async fn old_gh_search_code(to_search: &str) -> i64 {
        dotenv().ok();

        let crab = octocrab::Octocrab::builder()
            .personal_token(std::env::var("GITHUB_TOKEN").unwrap())
            .build()
            .unwrap();

        let cnt: i64;
        if let Some(q) = gh_search_preprocess(to_search) {
            cnt = crab.search().code(&q).send().await.map_or_else(
                |e| {
                    eprintln!("Error: github code search:\n{e}");
                    -2
                },
                |p| {
                    p.total_count
                        .map(|n| i64::try_from(n).unwrap_or(-3))
                        .unwrap_or(-4)
                },
            );
        } else {
            cnt = -1;
        }
        cnt
    }

    /// # Error code meaning
    /// * `-1` - `to_search` is empty
    /// * `-2` - Error when querying
    /// * `-3` - n too large to fit into i64
    /// * `-4` - page.total_count is None
    /// * other- HTTP status code
    async fn my_gh_search_code(to_search: &str) -> i64 {
        dotenv().ok();
        let crab = octocrab::Octocrab::builder()
            .personal_token(std::env::var("GITHUB_TOKEN").unwrap())
            .build()
            .unwrap();

        let cnt: i64;
        let max_retry = 3;

        if let Some(q) = gh_search_preprocess(to_search) {
            let mut resp = crab.search().code(&q).send_res().await.unwrap();

            let mut flag_retry: i32 = max_retry; // maximum retry time
            while flag_retry > 0 {
                // https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#secondary-rate-limits
                if resp.status().as_u16() == 403 && resp.headers().contains_key("retry-after") {
                    let secs = resp
                        .headers()
                        .get("retry-after")
                        .unwrap()
                        .to_str()
                        .unwrap()
                        .parse::<u64>()
                        .unwrap();
                    println!("retry-after {}s", secs);
                    thread::sleep(Duration::from_secs(secs + 5));
                    flag_retry -= 1;
                } else if resp.status().as_u16() == 403
                    && resp.headers().contains_key("x-ratelimit-reset")
                {
                    let until_epoch = resp
                        .headers()
                        .get("x-ratelimit-reset")
                        .unwrap()
                        .to_str()
                        .unwrap()
                        .parse::<u64>()
                        .unwrap();
                    let now_epoch = SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs();
                    if until_epoch > now_epoch {
                        println!("x-ratelimit-reset {}s", until_epoch - now_epoch);
                        thread::sleep(Duration::from_secs(until_epoch - now_epoch + 5));
                    }
                    flag_retry -= 1;
                } else {
                    break;
                }
                if flag_retry > 0 {
                    println!("Retry-{}:", max_retry - flag_retry);
                    resp = crab.search().code(&q).send_res().await.unwrap();
                }
            }
            if !resp.status().is_success() {
                let s_code = resp.status().as_u16() as i64;
                return 0 - s_code;
            } else {
                cnt = Page::<Code>::from_response(octocrab::map_github_error(resp).await.unwrap())
                    .await
                    .map_or_else(
                        |e| {
                            println!("Error: github code search:\n{e}");
                            -2
                        },
                        |p| {
                            p.total_count
                                .map(|n| i64::try_from(n).unwrap_or(-3))
                                .unwrap_or(-4)
                        },
                    );
            }
        } else {
            cnt = -1;
        }
        cnt
    }

    pub async fn gh_search_code(to_search: &str) -> GHRet {
        GHRet {
            total_count: my_gh_search_code(to_search).await,
            url: gh_search_url(to_search),
        }
    }

    #[test]
    fn test_search_preprocess() {
        let s1 = " .doe@jagare.in\"))";
        println!("{}", gh_search_preprocess(s1).unwrap());
    }
}

pub mod analysis {
    use super::db_ops::QueryItem;

    pub fn label_distribution(query_items: &Vec<QueryItem>) -> ([u32; 5], [u32; 5]) {
        type LabelCounter = [u32; 5];
        let mut cnt_sec: LabelCounter = [0; 5];
        let mut cnt_pri: LabelCounter = [0; 5];
        fn add_one(cnt: &mut LabelCounter, label: &str) {
            match label {
                "unknown" => cnt[0] += 1,
                "yes" => cnt[1] += 1,
                "likely" => cnt[2] += 1,
                "notlikely" => cnt[3] += 1,
                "no" => cnt[4] += 1,
                _ => panic!("label mismatch {}", label),
            }
        }
        for query in query_items.iter() {
            match query.category.split_once(":").unwrap().0 {
                "Secret" => add_one(&mut cnt_sec, &query.label),
                "Privacy" => add_one(&mut cnt_pri, &query.label),
                _ => panic!(
                    "Category does not match! ID: {}, Category: {}",
                    query.id, query.category
                ),
            }
        }
        (cnt_sec, cnt_pri)
    }
}

#[cfg(test)]
mod tests {

    use rocket::tokio;

    #[tokio::test]
    async fn test_gh_search() {
        let test_tuple_1 = (
            "13066909086",
            10_i64,
            "https://github.com/search?q=13066909086&type=code",
        );
        let test_tuple_2 = (
            "zhgyrjxng",
            0,
            "https://github.com/search?q=zhgyrjxng&type=code",
        );

        let test_ret_1 = super::gh_search::gh_search_code(test_tuple_1.0).await;
        assert_eq!(test_ret_1.total_count, test_tuple_1.1);
        assert_eq!(test_ret_1.url, test_tuple_1.2);

        let test_ret_2 = super::gh_search::gh_search_code(test_tuple_2.0).await;
        assert_eq!(test_ret_2.total_count, test_tuple_2.1);
        assert_eq!(test_ret_2.url, test_tuple_2.2);
    }
}
