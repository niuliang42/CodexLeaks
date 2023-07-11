#[macro_use]
extern crate rocket;
extern crate rocket_dyn_templates;

use std::io::{self, Write};
use std::{thread, time};

use rocket::form::Form;
use rocket::response::Redirect;
use rocket_db_pools::Connection;
use rocket_db_pools::Database;
use rocket_dyn_templates::{context, tera::Tera, Template};

use annotator::db_ops::DBOpenAI;

use annotator::db_ops::{
    load_data_all, load_data_by_id, load_data_by_label, load_data_by_milabel, load_data_to_look, load_data_to_look_label,
    update_data, update_ghitem,
};
use annotator::db_ops::{GhItem, Item2Update, UpdateOpt};
use annotator::gh_search::gh_search_code;

#[get("/")]
pub async fn web_index(mut db: Connection<DBOpenAI>) -> Template {
    let query_items = load_data_all(&mut *db).await;
    Template::render(
        "index",
        context! {
            items: query_items,
        },
    )
}

// For Ajax updating only the modified item
#[post("/ajax/update", data = "<label_form>")]
pub async fn web_update_ajax(
    mut db: Connection<DBOpenAI>,
    label_form: Form<Item2Update>,
) -> Template {
    println!("{:#?}", label_form);
    let item = label_form.into_inner();
    let id = item.id;
    if let Err(_) = update_data(&mut *db, &item, UpdateOpt::LabelOnly).await {
        error_!("DB `label` update error! id = {id}");
    };

    let item = load_data_by_id(&mut *db, id).await.unwrap();

    Template::render(
        "item",
        context! {
            s: item,
        },
    )
}

// For Ajax run github search for a single item
#[post("/ajax/search", data = "<label_form>")]
pub async fn web_gh_search_ajax(
    mut db: Connection<DBOpenAI>,
    label_form: Form<Item2Update>,
) -> Template {
    println!("{:#?}", label_form);
    let item = label_form.into_inner();
    let id = item.id;
    if let Err(_) = update_data(&mut *db, &item, UpdateOpt::ToSearchOnly).await {
        error_!("DB `to_search` update error! id = {id}");
    };

    if !item.to_search.is_empty() {
        let ret = gh_search_code(&item.to_search).await;
        if let Err(_) = update_ghitem(
            &mut *db,
            &GhItem {
                query_id: id,
                total_count: ret.total_count,
                url: ret.url.clone(),
            },
        )
        .await
        {
            error_!("DB github update error! id = {id}");
        };
    } else {
        println!("`to_search` is empty, will not run github search.");
    }

    let item = load_data_by_id(&mut *db, id).await.unwrap();

    Template::render(
        "item",
        context! {
            s: item,
        },
    )
}

#[get("/search")]
pub async fn web_search(mut db: Connection<DBOpenAI>) -> Redirect {
    let query_items = load_data_all(&mut *db).await;
    for (_, item) in query_items[..].iter().enumerate() {
        thread::sleep(time::Duration::from_secs_f32(6.5)); // rate limit: 10/min

        print!("{} ", item.id);
        io::stdout().flush().unwrap();

        if !item.to_search.is_empty() {
            let ret = gh_search_code(&item.to_search).await;
            if let Err(_) = update_ghitem(
                &mut *db,
                &GhItem {
                    query_id: item.id,
                    total_count: ret.total_count,
                    url: ret.url.clone(),
                },
            )
            .await
            {
                error_!("DB github update error! id = {}", item.id);
            } else {
                print!(",");
                io::stdout().flush().unwrap();
            }
        }
    }
    Redirect::to(uri!(web_index))
}

#[get("/label/<label>")]
pub async fn web_index_label(mut db: Connection<DBOpenAI>, label: &str) -> Template {
    let choices = load_data_by_label(&mut *db, label).await;
    Template::render(
        "index",
        context! {
            items: choices,
        },
    )
}

#[get("/milabel/<label>")]
pub async fn web_index_milabel(mut db: Connection<DBOpenAI>, label: &str) -> Template {
    let choices = load_data_by_milabel(&mut *db, label).await;
    Template::render(
        "index",
        context! {
            items: choices,
        },
    )
}

#[get("/tolook")]
pub async fn web_index_tolook(mut db: Connection<DBOpenAI>) -> Template {
    let choices = load_data_to_look(&mut *db).await;
    Template::render(
        "index",
        context! {
            items: choices,
        },
    )
}

#[get("/tolook/<label>")]
pub async fn web_index_tolook_label(mut db: Connection<DBOpenAI>, label: &str) -> Template {
    let choices = load_data_to_look_label(&mut *db, label).await;
    Template::render(
        "index",
        context! {
            items: choices,
        },
    )
}

pub fn customize(tera: &mut Tera) {
    tera.add_raw_template(
        "about.html",
        r#"
        {% extends "base" %}

        {% block content %}
            <section id="about">
              <h1>About - Here's another page!</h1>
            </section>
        {% endblock content %}
    "#,
    )
    .expect("valid Tera template");
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount(
            "/",
            routes![
                web_index,
                web_index_label,
                web_index_milabel,
                web_index_tolook,
                web_index_tolook_label,
                web_update_ajax,
                web_gh_search_ajax,
                web_search
            ],
        )
        .attach(DBOpenAI::init())
        .attach(Template::custom(|engines| {
            customize(&mut engines.tera);
        }))
}
