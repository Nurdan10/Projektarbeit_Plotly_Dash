import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import json


df = pd.read_csv('full_immo_data.csv')
df['plz_str'] = df['geo_plz'].astype(str)  

with open('georef-germany-postleitzahl.geojson', 'r') as f:
    geojson_data = json.load(f)

plz_stadt = []
for feature in geojson_data['features']:
    plz = feature['properties']['plz_code']
    stadt = feature['properties']['plz_name']
    land = feature['properties']['lan_name']  # ✅ eyalet
    plz_stadt.append({'plz_code': plz, 'city_name': stadt, 'lan_name': land})

plz_stadt_df = pd.DataFrame(plz_stadt)
plz_stadt_df['plz_code'] = plz_stadt_df['plz_code'].astype(str).str.zfill(5)

df_map = df.groupby('plz_str')['base_rent'].mean().reset_index()
df_map['plz_str'] = df_map['plz_str'].str.zfill(5)

df_map = pd.merge(df_map, plz_stadt_df, left_on='plz_str', right_on='plz_code', how='left')


# 📌 Erstellen Dash App
app = dash.Dash(__name__)
server = app.server

# 🧮 Spalten
categorical_cols = [
    'regio_1', 'type_of_flat', 'heating_type_cleaned', 'telekom_tv_offer', 'interior_qual', 'pets_allowed', 
    'type_of_flat', 'upload_speed_category',  'firing_types_simplified', 'condition_grouped', 'refurbish_category', 'year_category'
]
numeric_cols = [
    'base_rent', 'total_rent', 'living_space', 'no_rooms_cleaned', 'floor',
    'no_park_spaces_cleaned', 'thermal_char', 'heating_costs', 'service_charge'
]   


# Dashboard Layout
app.layout = html.Div([
    html.H1('🏡 Mietanalyse Dashboard (Deutschland)', style={'textAlign': 'center'}),

    dcc.Tabs([
        dcc.Tab(label='Übersicht', children=[
            html.Div([
                html.H3('📊 Durchschnittswerte'),
                html.P(f"Durchschnittliche Kaltmiete: {df['base_rent'].mean():.2f} €"),
                html.P(f"Durchschnittliche Gesamtmiete: {df['total_rent'].mean():.2f} €"),
                html.P(f"Median der Kaltmiete: {df['base_rent'].median():.2f} €"),
                html.P(f"Durchschnittliche Wohnfläche: {df['living_space'].mean():.2f} m²")
            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Regionale Verteilung (Treemap)', children=[
            html.Div([
                html.H4('Treemap der Regionen'),
                dcc.Graph(
                    id='treemap-plot',
                    figure=px.treemap(df, path=['regio_1', 'regio_2', 'region_combo'],
                                  #color='base_rent', color_continuous_scale='Viridis',
                                  title="Verteilung der Daten nach Region (Treemap)")
                )
            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Kategorische Analyse', children=[
            html.Div([
                html.Label('Wähle eine kategorische Variable:'),
                dcc.Dropdown(id='cat-col', options=[{'label': col, 'value': col} for col in categorical_cols],
                             value='type_of_flat'),
                dcc.Graph(id='cat-barplot')
            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Numerische Analyse', children=[
            html.Div([
                html.Label('Wähle eine numerische Variable:'),
                dcc.Dropdown(id='num-col', options=[{'label': col, 'value': col} for col in numeric_cols],
                             value='living_space'),
                dcc.Graph(id='num-histplot')
            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Korrelation', children=[
            html.Div([
                html.Label('X-Achse (numerisch):'),
                dcc.Dropdown(id='x-col', options=[{'label': col, 'value': col} for col in numeric_cols],
                             value='living_space'),

                html.Label('Y-Achse (numerisch):'),
                dcc.Dropdown(id='y-col', options=[{'label': col, 'value': col} for col in numeric_cols],
                             value='base_rent'),

                dcc.Graph(id='scatterplot')
            ], style={'padding': '20px'})
        ]),

        dcc.Tab(label='Geografische Karte', children=[
            html.Div([
                dcc.Graph(id='map-plot')  
            ], style={'padding': '20px'})
        ])
    ])
])
  

# 🎯 Callbacks
@app.callback(
    Output('cat-barplot', 'figure'),
    Input('cat-col', 'value')
)
def update_cat_plot(col):
    df_grouped = df.groupby(col)['base_rent'].mean().reset_index()
    df_grouped = df_grouped.sort_values(by='base_rent', ascending=False)

    fig = px.bar(df_grouped,
                 x=col, y='base_rent',
                 color='base_rent',
                 title=f'Durchschnittliche Miete nach {col}',
                 color_continuous_scale='Viridis_r')
    fig.update_layout(xaxis_tickangle=45)
    return fig

@app.callback(
    Output('num-histplot', 'figure'),
    Input('num-col', 'value')
)
def update_num_plot(col):
    fig = px.histogram(df, x=col, nbins=40,
                       title=f'Verteilung von {col}',
                       color_discrete_sequence=['#636EFA'])
    return fig

@app.callback(
    Output('scatterplot', 'figure'),
    [Input('x-col', 'value'), Input('y-col', 'value')]
)
def update_scatter(x_col, y_col):
    fig = px.scatter(df, x=x_col, y=y_col,
                     title=f'Zusammenhang: {x_col} vs. {y_col}',
                     color='type_of_flat',
                     opacity=0.6)
    return fig
    
@app.callback(
    Output('map-plot', 'figure'),
    Input('cat-col', 'value')  # kullanmıyorsan '_' yap
)
def update_map_plot(_):
    fig = px.choropleth(
        df_map,
        geojson=geojson_data,
        locations='plz_str',
        featureidkey='properties.plz_code',
        color='base_rent',
        hover_data={
            'plz_str': True,
            'city_name': True,
            'lan_name': True, 
            'base_rent': ':.2f'
        },
        color_continuous_scale="Viridis_r",
        title="Durchschnittliche Miete pro PLZ"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
    return fig



# 🔄 Server Start
if __name__ == '__main__':
    app.run(debug=True)
