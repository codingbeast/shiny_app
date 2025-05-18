from flask import Flask, Response, render_template, request, jsonify, send_file
from matplotlib.figure import Figure
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg for non-interactive plotting
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.collections import PatchCollection
import matplotlib.gridspec as gridspec
from datetime import datetime
import numpy as np
from matplotlib.colors import ListedColormap
import io
import base64
import os
# Constants
COUNTRY_PATH = "ISO_country_names.txt"
OSAC_DAILY_PATH = "OSAC_daily.csv"
OSAC_MONTHLY_PATH = "OSAC_monthly.csv"
DEFAULT_COUNTRY = "United States of America"
DEFAULT_PERIOD = "monthly"

class DataParser:


    @staticmethod
    def fast_plot_monthly(df, ax,  n_circles=11):
        circle_radius = 0.15
        circle_gap = 0.4
        bar_width = 0.6

        patches = []
        colors = []

        bar_height = n_circles * (2 * circle_radius + circle_gap)

        for idx, row in enumerate(df[['protest', 'anticipated', 'suppression']].values):
            p, a, s = row

            if (a, s) == (1,1):
                color = 'green'
                solid = True
            elif (a, s) == (1,0):
                color = 'gray'
                solid = True
            elif (a, s) in (0,1):
                color = 'green'
                solid = False
            elif (a, s) == (0,0):
                color = 'gray'
                solid = False
            else:
                continue  # (0,0,0)

            if solid:
                ax.bar(idx, bar_height, color=color, width=bar_width)
            else:
                for i in range(n_circles):
                    y = i * (2 * circle_radius + circle_gap) + circle_radius
                    patches.append(Circle((idx, y), circle_radius))
                    colors.append(color)

        if patches:
            collection = PatchCollection(patches, facecolor=colors, edgecolor=colors)
            ax.add_collection(collection)

        # Formatting
        ax.set_xlim(-0.5, len(df) - 0.5)
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df['formatted_date'],fontsize=9)
        ax.set_ylim(0, bar_height + 1)
        ax.set_yticks([])
        # Set equal aspect ratio and manually adjust limits
        ax.set_aspect('equal', adjustable='box')
        # Remove the graph border
        # for spine in ax.spines.values():
        #     spine.set_visible(False)
    @staticmethod
    def calculate_preventiveness(row):
        protest = row['protest']
        anticipated = row['anticipated']
        suppression = row['suppression']

        # Match exactly against the known patterns
        if protest == 1 and anticipated == 1 and suppression == 0:
            return 0
        elif protest == 1 and anticipated == 0 and suppression == 1:
            return 1
        elif protest == 0 and anticipated == 0 and suppression == 0:
            return 1
        elif protest == 1 and anticipated == 0 and suppression == 0:
            return 1
        elif protest == 0 and anticipated == 0 and suppression == 1:
            return 1
        elif protest == 0 and anticipated == 1 and suppression == 0:
            return 0
        elif protest == 0 and anticipated == 1 and suppression == 1:
            return 1
        elif protest == 1 and anticipated == 1 and suppression == 1:
            return 0
        else:
            return 0  # Default case (for safety)

    @staticmethod
    def monthly_df_parsed(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()  # Ensure it's a deep copy, not a view
        current_date = pd.to_datetime('today')
        df.rename(columns={'month': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m', errors='coerce')
        df['formatted_date'] = df['date'].dt.strftime('%b\n%Y')
        filtered_df = df[(df['date'] >= current_date - pd.DateOffset(months=12))]
        filtered_df = filtered_df.sort_values(by='date', ascending=True)
        filtered_df = filtered_df.reset_index(drop=True)
        return filtered_df
    @staticmethod
    def monthly_df_preventiveness(df: pd.DataFrame) -> pd.DataFrame:
        # Clean column names first
        df = DataParser.monthly_df_parsed(df)
        df.columns = df.columns.str.strip().str.lower()
        
        # Verify required columns exist
        required = {'protest', 'anticipated', 'suppression'}
        missing = required - set(df.columns)
        if missing:
            available = list(df.columns)
            raise ValueError(
                f"Missing columns {missing}. Available columns: {available}"
            )
        
        # Calculate preventiveness
        df['index of preventiveness'] = df.apply(
            DataParser.calculate_preventiveness, 
            axis=1
        )
        
        # Rename columns (optional)
        # df = df.rename(columns={
        #     'protest': 'Any Protest',
        #     'suppression': 'Any Suppressed Protest',
        #     'anticipated': 'Any Anticipated Protest',
        # })
        
        return df

    @staticmethod
    def get_monthy_df_preventiveness_titles() -> list:
        return ['Any Protest', 'Any Anticipated Protest', 'Any Suppressed Protest','Index of Preventiveness']
    
    @staticmethod
    def daily_df_parsed(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()  # Ensure it's a deep copy, not a view
        df.rename(columns={'month': 'date'}, inplace=True)
        current_date = pd.to_datetime('today')
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        df['formatted_date'] = df['date'].dt.strftime('%b %d\n%Y')
        filtered_df = df.sort_values(by='date', ascending=True)
        filtered_df = filtered_df[
            (filtered_df['date'] >= current_date - pd.DateOffset(days=31)) &
            (filtered_df['date'] <= current_date)
        ]
        filtered_df = filtered_df.reset_index(drop=True)
        filtered_df['group'] = filtered_df.index // 2
        grouped_df = (
            filtered_df
            .groupby('group')
            .agg({
                'country': 'first',
                'date': 'last',  # Take second date in the pair
                'protest': 'max',
                'suppression': 'max',
                'anticipated': 'max',
            })
            .reset_index(drop=True)
        )

        # Add formatted_date again
        grouped_df['formatted_date'] = grouped_df['date'].dt.strftime('%b %d\n%Y')
        return grouped_df
    @staticmethod
    def draw_solid_bar(ax, color, n_circles=5):
        circle_radius = 0.09
        circle_gap = 0.2
        bar_height = 0.3
        bar_length = n_circles * (2 * circle_radius + circle_gap)
        total_width = bar_length + 1
        start_x = (total_width - bar_length) / 2
        
        ax.barh([0], [bar_length], left=start_x, color=color, height=bar_height)
        DataParser.setup_axes(ax, total_width)
    @staticmethod
    def draw_circle_bar(ax, color, n_circles=5):
        circle_radius = 0.09
        circle_gap = 0.2
        bar_length = n_circles * (2 * circle_radius + circle_gap)
        total_width = bar_length + 1
        start_x = (total_width - bar_length) / 2
        
        patches = []
        for i in range(n_circles):
            x = start_x + i * (2 * circle_radius + circle_gap) + circle_radius
            patches.append(Circle((x, 0), circle_radius))
        
        collection = PatchCollection(patches, facecolor=color, edgecolor=color)
        ax.add_collection(collection)
        DataParser.setup_axes(ax, total_width)
    @staticmethod
    def setup_axes(ax, total_width):
        ax.set_xlim(0, total_width)
        ax.set_ylim(-0.5, 0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis('off')
        ax.set_aspect('auto')
    @staticmethod
    def draw_bar(ax, p, a, s):
        if (p, a, s) == (1, 1, 1):
            DataParser.draw_solid_bar(ax, 'green')
        elif (p, a, s) == (1, 1, 0):
            DataParser.draw_solid_bar(ax, 'gray')
        elif (p, a, s) in [(1, 0, 1), (0, 1, 1)]:
            DataParser.draw_circle_bar(ax, 'green')
        elif (p, a, s) in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            DataParser.draw_circle_bar(ax, 'gray')
    @staticmethod
    def example_generator():
        fig = plt.figure(figsize=(2, 4))  # You can tweak the figure size

        data = [
            (0, 0, 1),
            (1, 0, 1),
            (1, 1, 0),
            (1, 1, 1),
        ]
        titles = [
            "None Anticipated,\nNone Suppressed",
            "None Anticipated,\nAny Suppressed",
            "Any Anticipated,\nNone Suppressed",
            "Any Anticipated,\nAny Suppressed",
        ]

        gs = gridspec.GridSpec(len(data)*2 + 1, 1, 
                            height_ratios=[0.3] + [0.8, 0.3]*len(data),
                            hspace=0.1)

        header_ax = fig.add_subplot(gs[0])
        header_ax.axis('off')
        header_ax.text(0.5, 0.5, "Protest Type", ha='center', va='center', fontsize=9)
        header_ax.plot([0.3, 0.7], [0.47, 0.47], color='black', linewidth=0.5)

        for i, (p, a, s) in enumerate(data, start=1):
            bar_ax = fig.add_subplot(gs[i*2 - 1])
            title_ax = fig.add_subplot(gs[i*2])

            DataParser.draw_bar(bar_ax, p, a, s)

            title_ax.axis('off')
            title_ax.text(0.5, 0.5, titles[i-1], ha='center', va='center', fontsize=7)

        return fig
    @staticmethod
    def fast_plot_preventiveness(df, ax):
        # Prepare dataframe
        df = df.copy()
        df['Index of Preventiveness'] = df.apply(DataParser.calculate_preventiveness, axis=1)
        df.rename(columns={
            'protest': 'Any Protest',
            'suppression': 'Any Suppressed Protest',
            'anticipated': 'Any Anticipated Protest',
        }, inplace=True)
        
        # Extract event data and transpose for imshow
        events = DataParser.get_monthy_df_preventiveness_titles()
        data_matrix = df[events].values.T  # Shape: (4 events × n months)

        # Custom colormap: white background only
        cmap = ListedColormap(['white'])

        # Display data (no gradient)
        im = ax.imshow(
            data_matrix, 
            cmap=cmap,
            aspect='auto',
            vmin=0,
            vmax=1
        )

        # Add text annotations
        for i in range(data_matrix.shape[0]):      # Rows (events)
            for j in range(data_matrix.shape[1]):  # Columns (months)
                ax.text(
                    j, i,
                    str(data_matrix[i, j]),
                    ha='center',
                    va='center',
                    color='black',
                    fontsize=10
                )

        # Customize axes
        ax.set_xticks([])
        ax.set_xticklabels([])  # No x-axis labels
        ax.set_yticks(np.arange(len(events)))
        ax.set_yticklabels(events,fontsize=9)
        ax.grid(False)
        
        # # Automatically adjust layout
        plt.tight_layout(pad=0)
        # Remove the graph border
        # for spine in ax.spines.values():
        #     spine.set_visible(False)

class DataManager:
    """Centralized data loading and management"""
    def __init__(self):
        self.daily_data = None
        self.monthly_data = None
        self.load_data()
    
    def load_data(self):
        """Load all required data files"""
        try:
            self.daily_data = pd.read_csv(OSAC_DAILY_PATH)
            self.monthly_data = pd.read_csv(OSAC_MONTHLY_PATH)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.daily_data = pd.DataFrame()
            self.monthly_data = pd.DataFrame()
    
    def get_country_data(self, period, country) -> pd.DataFrame:
        """Get data for specific country and period"""
        data = self.daily_data if period == "daily" else self.monthly_data
        if 'country' in data.columns:
            return data[data['country'] == country]
        return pd.DataFrame()

class Helper:
    def __init__(self):
        pass
    def get_country_names(self):
        with open(COUNTRY_PATH, 'r', encoding='utf-8') as f:
            country_names = f.read().splitlines()
            return country_names


app = Flask(__name__)
helper = Helper()
data_manager = DataManager()

@app.route('/')
def home():
    country_names = helper.get_country_names()
    period = request.args.get('period',DEFAULT_PERIOD)
    country = request.args.get('country',DEFAULT_COUNTRY)
    country_data = data_manager.get_country_data(period, country)
    if not country_data.empty:
        if period=="monthly":
            parsed_df = DataParser.monthly_df_parsed(country_data)
        elif period == "daily":
            parsed_df = DataParser.daily_df_parsed(country_data)
    else:
        parsed_df = pd.DataFrame()
    # --- Generate chart only if valid dataframe ---
    img_data = None
    img_data_buttom = None
    if not parsed_df.empty:
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1)
        DataParser.fast_plot_monthly(parsed_df, ax)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.01)
        buf.seek(0)
        img_data = base64.b64encode(buf.read()).decode('utf-8')
        #-- genrate chart 2 buttom ====
        if period=="monthly":
            fig = Figure(figsize=(10, 2))
            ax = fig.add_subplot(1, 1, 1)

            DataParser.fast_plot_preventiveness(parsed_df, ax)

            # Save to BytesIO and return as image
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight",pad_inches=0.01)
            buf.seek(0)
            img_data_buttom = base64.b64encode(buf.read()).decode('utf-8')
    context = {
        "selected_country_name" : DEFAULT_COUNTRY,
        "country_names" : country_names,
        "img_data" : img_data,
        "img_data_buttom" : img_data_buttom,
        "is_month" : True if period == "monthly" else False
    }
    return render_template('index.html',**context)

@app.route('/example_plot')
def serve_plot():
    fig = DataParser.example_generator()
    output = io.BytesIO()
    fig.savefig(output, format='png', bbox_inches='tight')
    plt.close(fig)  # Prevent memory leaks
    output.seek(0)
    return Response(output.getvalue(), mimetype='image/png')

@app.route("/preventiveness_plot")
def serve_preventiveness_plot():
    # Sample data (replace this with actual data)
    df = pd.DataFrame({
        'protest': [0, 1, 0, 1],
        'suppression': [0, 0, 1, 1],
        'anticipated': [1, 0, 1, 1]
    })

    fig = Figure(figsize=(10, 2))
    ax = fig.add_subplot(1, 1, 1)

    DataParser.fast_plot_preventiveness(df, ax)

    # Save to BytesIO and return as image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0')
