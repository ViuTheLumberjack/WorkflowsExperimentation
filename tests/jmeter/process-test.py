import pandas as pd
from utility import OUPUT_PATH, plot_results, plot_results_clamp

def teardown_removal(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure group threads are non-decreasing.
    valid_rows = []
    previous_grpThreads = df.iloc[0]['grpThreads']

    for index, row in df.iterrows():
        current_grpThreads = row['grpThreads']
        if current_grpThreads >= previous_grpThreads:
            valid_rows.append(index)
            previous_grpThreads = current_grpThreads
    
    df = df.loc[valid_rows]

    return df

def is_outlier(s: pd.Series) -> pd.Series:
    Q1 = s.quantile(0.25)
    Q3 = s.quantile(0.75)
    IQR = Q3 - Q1

    return (s < (Q1 - 1.5 * IQR)) | (s > (Q3 + 1.5 * IQR))


if __name__ == '__main__':
    # Load the data.
    df = pd.read_csv(OUPUT_PATH)

    # Filter only sequential requests.
    # df = df[df['label'].str.contains('Parallel')].reset_index(drop=True)
    # df = df[df['IdleTime'] > 0].reset_index(drop=True)

    # Drop failed requests.
    # df = df[df['responseCode'] == 200].reset_index(drop=True)

    # # Drop conecting time responses.
    df = df[df['Connect'] <= 0].reset_index(drop=True)

    # # Drop teardown requests.
    df = teardown_removal(df)
    df = df[df['grpThreads'] <= 50].reset_index(drop=True)

    # Drop outliers for each group of threads interquartile range.
    df = df[~df.groupby('grpThreads')['elapsed'].transform(is_outlier)].reset_index(drop=True)

    # Calculate response mean time for each group of threads.
    results = df.groupby('grpThreads').agg({'elapsed': 'mean', 'Latency': 'mean', 'IdleTime': 'mean', 'Connect': 'mean'}).reset_index()
    results['total_requests'] = df.groupby('grpThreads')['elapsed'].count().values
    print(results)

    # Plot the results.
    plot_results_clamp(df, results)