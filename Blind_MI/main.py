from utils import *
import json
from tqdm import tqdm
import tensorflow as tf
from transformers import GPT2Tokenizer
from sklearn.metrics import (
    f1_score,
    recall_score,
    accuracy_score,
    precision_score,
    balanced_accuracy_score,
)
import time
from scipy.stats import mode


# the attack
def blind(
    log_prob, g_truth, choices, pred, true, slices, lo, hi, id, algo, to_0=0, to_1=1
):

    mix = np.array(log_prob).astype("float32")

    # perp--------
    if algo == 0:
        mix = np.c_[mix, mix]
    # ---------

    m_pred = threshold_Divide(mix, lo, hi)
    ## perp---------
    if algo == 0:
        mix = mix[:, 0]
        mix = np.c_[mix.reshape(-1, 1), np.zeros((mix.shape[0], 1))].astype("float32")
    ##--------------

    data = (
        tf.data.Dataset.from_tensor_slices(
            (mix, g_truth.astype(int), m_pred, choices, id)
        )
        .shuffle(buffer_size=mix.shape[0])
        .batch(4000)
        .prefetch(tf.data.experimental.AUTOTUNE)
    )
    # true is the id of the sample in the original db, mix is perplexity, pred is the prediction
    m_pred, m_true, choices_string, m_id = [], [], [], []
    for (
        mix_batch,
        m_true_batch,
        m_pred_batch,
        choices_string_batch,
        m_id_batch,
    ) in data:
        m_pred_batch = m_pred_batch.numpy()

        Flag = True
        while Flag:

            dis_ori = mmd_loss(
                mix_batch[m_pred_batch.astype(bool) == False],
                mix_batch[m_pred_batch.astype(bool)],
                weight=1,
            )
            Flag = False
            if to_1:

                for index, item in tqdm(enumerate(mix_batch)):
                    if m_pred_batch[index] == 0:
                        m_pred_batch[index] = 1
                        mix_1 = mix_batch[m_pred_batch.astype(bool)]
                        mix_2 = mix_batch[m_pred_batch.astype(bool) == False]
                        dis_new = mmd_loss(mix_2, mix_1, weight=1)
                        if dis_new < dis_ori:
                            m_pred_batch[index] = 0
                        else:
                            Flag = True
                            dis_ori = tf.identity(dis_new)
            if to_0 or (to_0 == 0 and to_1 == 0):
                for index, item in tqdm(enumerate(mix_batch)):
                    if m_pred_batch[index] == 1:
                        m_pred_batch[index] = 0
                        mix_1 = mix_batch[m_pred_batch.astype(bool)]
                        mix_2 = mix_batch[m_pred_batch.astype(bool) == False]
                        dis_new = mmd_loss(mix_2, mix_1, weight=1)
                        if dis_new < dis_ori:
                            m_pred_batch[index] = 1
                        else:
                            Flag = True
                            dis_ori = tf.identity(dis_new)
        print("Loop finished")
        m_pred.append(m_pred_batch)
        m_true.append(m_true_batch)
        choices_string.append(choices_string_batch)
        m_id.append(m_id_batch)

    m_true, m_pred, choices_string, m_id = (
        np.concatenate(m_true, axis=0),
        np.concatenate(m_pred, axis=0),
        np.concatenate(choices_string, axis=0),
        np.concatenate(m_id, axis=0),
    )
    true.append(m_true)
    pred.append(m_pred)
    slices.append(choices_string)
    return m_id


def extract(name):
    print(name)
    connection = sqlite3.connect("../content/results" + name + ".db")
    cursor = connection.cursor()
    cursor.execute("SELECT class,log_prob FROM responses;")
    results = np.array(cursor.fetchall(), dtype=object)

    cursor.execute("SELECT choice FROM responses;")
    choices = cursor.fetchall()

    g_truth = np.array(results)[:, 0]
    log_prob = np.array(results)[:, 1]

    perplex = np.array([np.mean(json.loads(l)) for i, l in enumerate(log_prob)])

    choices = np.array(choices)
    cursor.execute("SELECT id FROM responses;")
    id = np.array(cursor.fetchall())[:, 0]

    cursor.close()
    connection.close()
    return log_prob, perplex, g_truth, choices, id


# tf.config.experimental.set_memory_growth(
#     tf.config.experimental.list_physical_devices("GPU")[0], True
# )
# tf.config.experimental.set_memory_growth(
#     tf.config.experimental.list_physical_devices("GPU")[1], True
# )


acc = []
f1 = []
per = []
rec = []
rat = []
algo = 0
trials = ["_8", "_9"]
lengths = [10, 15]
for tri, db in enumerate(trials):
    acc.append([])
    f1.append([])
    per.append([])
    rec.append([])
    rat.append([])
    print("Trial: ", db)
    for n_tok in lengths:
        #load from database
        log_prob, perplex, g_truth, choices, id = extract(str(n_tok) + db)
        # save perplexity of each entry
        perp_s = {ind: perplex[i] for i, ind in enumerate(id)}
        # results of the attack
        pred, true = [], []
        sl = []

        # 0: perplexity 1:n_gram 2:log_probabilities 3:multi_perp
        if algo == 0:
            features = perplex
        if algo == 1:
            ## sliding windows ------------------------------
            features = np.array(
                [
                    [
                        np.mean(json.loads(l)[k : k + (int(0.9 * n_tok))])
                        for k in range(len((json.loads(l))) - (int(0.9 * n_tok) - 1))
                    ]
                    for i, l in enumerate(log_prob)
                ]
            )
        ##-------------------------------

        # log_prob-------------------------
        if algo == 2:
            features = np.array([(json.loads(l)) for i, l in enumerate(log_prob)])
        if algo == 3:
            # subsequnces---------------------
            ratio = int(0.1 * n_tok)
            features = perplex
            for le in range(ratio, n_tok, ratio):

                slices = [
                    np.argmax(
                        [
                            np.mean(log_prob[l][n : n + le])
                            for n in range(len(log_prob[l]) - le)
                        ]
                    )
                    for l, k in enumerate(perplex)
                ]
                features = np.c_[
                    features,
                    np.array(
                        [
                            np.mean(log_prob[l][slices[l] : le + slices[l]])
                            for l, k in enumerate(perplex)
                        ]
                    ),
                ]

        # --------------------
        arg = {
            "log_prob": features,
            "g_truth": g_truth,
            "choices": choices,
            "pred": pred,
            "true": true,
            "slices": sl,
            "lo": 0.25,
            "hi": 0.75,
            "id": id,
            "algo": algo,
            "to_0": 0,
            "to_1": 1,
        }




        id = blind(**arg)
        print(db, n_tok)
        #metrics
        acc[tri].append(accuracy_score(true[-1], pred[-1]))
        f1[tri].append(f1_score(true[-1], pred[-1], average=None))
        rec[tri].append(recall_score(true[-1], pred[-1], average=None))
        per[tri].append(precision_score(true[-1], pred[-1], average=None))
        rat[tri].append(np.sum(pred) / len(perplex))
        print("Accuracy: ", acc[tri][-1])
        print("F1 : ", f1[tri][-1])
        print("Recall : ", rec[tri][-1])
        print("Percision: ", per[tri][-1])
        print("Ratio: ", rat[tri][-1])



        #save results
        cursor, conn = create_database(n_tok, db)
        sqlite_insert_query = """INSERT INTO responses
                            (id, choice, pred,true,perp) 
                            VALUES 
                            (?,?,?,?,?)"""

        
        for j, i in enumerate(id):

            count = cursor.execute(
                sqlite_insert_query,
                (
                    int(i),
                    sl[0][j][0].decode("utf-8"),
                    int(pred[-1][j]),
                    int(true[-1][j]),
                    float(perp_s[i]),
                ),
            )

        conn.commit()
        # print("Record inserted successfully into SqliteDb_developers table ", cursor.rowcount)
        cursor.close()
print("Final: ")
acc_avg = np.mean(acc, axis=0) * 100
f1_avg = np.mean(f1, axis=0) * 100
rec_avg = np.mean(rec, axis=0) * 100
per_avg = np.mean(per, axis=0) * 100
rat_avg = np.mean(rat, axis=0) * 100

# json
# for i,n in enumerate([10]):
# i = 0
# out = {
#     str(r): {
#         "Accuracy": (acc_avg[i]),
#         "F1": str(f1_avg[i]),
#         "Recall": str(rec_avg[i]),
#         "Percision": str(per_avg[i]),
#         "Rat": str(rat_avg[i]),
#     }
# }

# if r != step:
#     with open("./rat_" + str(step) + ".json", "a") as f:
#         json.dump(out, f)
# else:
#     with open("./rat_" + str(step) + ".json", "w") as f:
#         json.dump(out, f)


# latex output of results
for i, n in enumerate(lengths):
    print(n)
    print(
        "&"
        + str(n)
        + "&"
        + "{:.2f}".format(acc_avg[i])
        + "&"
        + "{:.2f}".format(f1_avg[i][0])
        + "&"
        + "{:.2f}".format(f1_avg[i][1])
        + "&"
        + "{:.2f}".format(rec_avg[i][0])
        + "&"
        + "{:.2f}".format(rec_avg[i][1])
        + "&"
        + "{:.2f}".format(per_avg[i][0])
        + "&"
        + "{:.2f}".format(per_avg[i][1])
        + "\\\\"
    )
