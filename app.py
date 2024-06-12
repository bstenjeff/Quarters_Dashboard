import csv
import pandas as pd
import numpy as np
import dash
from dash import Dash, html, dcc,Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import datetime
from datetime import datetime as dt
import time
import json
import plotly.express as px
from dateutil.rrule import rrule, DAILY
pd.set_option('display.max_rows', 100)
import html2text
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import requests
from io import BytesIO

Reach_allpastoralreports_raw = pd.read_csv("https://docs.google.com/spreadsheets/d/1TgamIbr9mn9Src1FHzoSTaW14ph2CGI3tvPOmnrP_vk/export?gid=0&format=csv",parse_dates=['Date'])
Students_2023_2024=pd.read_csv("https://docs.google.com/spreadsheets/d/17dcVZodf-u99JQQD-6iSEz2U--KXtU8F6B5fM8hdOSY/export?gid=0&format=csv")
#Reach_allpastoralreports_raw = pd.read_csv('REACH Pastoral Report - Data Processing - Export.csv')
#Students_2023_2024 = pd.read_csv('REACH Pastoral Report - Data Processing - Update List of All Students.csv')
allpastoralreports_processed = pd.DataFrame([],columns = Reach_allpastoralreports_raw.columns.tolist())
Reach_allpastoralreports_raw["External PK"] = Reach_allpastoralreports_raw["External PK"].astype(str)

row = 0
pks = []
for pklist in Reach_allpastoralreports_raw["External PK"]:
  pklist = pklist.split(',')
  pklist = [p.strip() for p in pklist]
  pks.append(pklist)
  row += 1

Reach_allpastoralreports_raw["External PK"] = pks
Reach_allpastoralreports_raw = Reach_allpastoralreports_raw.explode("External PK",ignore_index =True)
Reach_allpastoralreports_raw["External PK"] = Reach_allpastoralreports_raw["External PK"].astype(float)

merged_df = pd.merge(Reach_allpastoralreports_raw, Students_2023_2024, on='External PK', how='left')
merged_df = merged_df.dropna(subset=["External PK"])
merged_df["Date"]=pd.to_datetime(merged_df["Date"],format ="%d/%m/%Y %H/%M" )
latestdate = merged_df["Date"].max()
merged_df = merged_df[merged_df["Pastoral Points"]<0]
merged_df["Details"] = [(html2text.html2text(str(d))).replace("Source: Pastoral","").replace("nan","").replace("[[This note was created from a duty report. Click here to view\nit.]](javascript:void\\(0\\);)","").replace("::amp::nbsp::semi::","") for d in merged_df["Details"]]

def unixTimeMillis(dt):
    ''' Convert datetime to unix timestamp '''
    return int(time.mktime(dt.timetuple()))

def unixToDatetime(unix):
    ''' Convert unix timestamp to datetime. '''
    return pd.to_datetime(unix,unit='s')

def getMarks(daterange):
    ''' Returns the marks for labeling.
        Every Nth value will be used.
    '''
    result = {}
    for i, date in enumerate(daterange):
        # Append value to dict
        if i%2==0:
            result[unixTimeMillis(date)] = {'label':str(date.strftime('%b-%d')),'style':{"white-space": "nowrap","margin":2}}
        else:
            result[unixTimeMillis(date)] = {'label':""}
    return result

def getMarks2(daterange):
    ''' Returns the marks for labeling.
        Every Nth value will be used.
    '''
    result = {}
    for i, date in enumerate(daterange):
          # Append value to dict
        result[unixTimeMillis(date)] = str(date.strftime('%b-%d'))

    return result

def description_card(tab):
    """

    :return: A Div containing dashboard title & descriptions.
    """
    if tab==1:
        descr = "Explore quarter metrics at TCS and filter by house, grade, a date range, and/or incident type."
        return html.Div(
                id="description-card1",
                children=[
                    html.Label("TCS Quarter Analytics"),
                    html.Div(
                        id="intro1",
                        children=descr,
                    ),
                ],style = {'text-indent':'25px'})
    else:
        descr = "Explore a specific student's quarter metrics and filter by incident type and/or a date range."
        return html.Div(
                id="description-card2",
                children=[
                    html.Label("TCS Quarter Analytics"),
                    html.Div(
                        id="intro2",
                        children=descr,
                    ),
                ],style = {'text-indent':'25px'})
    
def plt_incident_type_bar1(df): # of occurences
    df = df[df["Pastoral Points"]<0]
    df["Pastoral Points"] = [-1*x for x in df["Pastoral Points"]]
    group_df_countincidenttype = df.groupby("Incident Type").agg({'Incident ID':'count'}).reset_index().rename(columns={"Incident ID":"Number of Occurences"}) # of occurences
    group_df_countincidenttype2 = df.groupby("Incident Type").agg({'External PK':'nunique'}).reset_index().rename(columns={"External PK":"Number of Student Offenders"}) # of individual student with at least 1 offense
    group_df_countincidenttype3 = df.groupby("Incident Type").agg({'Pastoral Points':'sum'}) #total quarter points
    #join together
    return (pd.merge(pd.merge(group_df_countincidenttype, group_df_countincidenttype2, on='Incident Type', how='left'),group_df_countincidenttype3,on='Incident Type', how='left')).sort_values(by=["Number of Occurences"],ascending = False)

def plt_incident_type_bar2(df): # of occurences
    df = df[df["Pastoral Points"]<0]
    df["Pastoral Points"] = [-1*x for x in df["Pastoral Points"]]
    group_df_countincidenttype = df.groupby("Incident Type").agg({'Incident ID':'count'}).reset_index().rename(columns={"Incident ID":"Number of Occurences"}) # of occurences
    group_df_countincidenttype2 = df.groupby("Incident Type").agg({'External PK':'nunique'}).reset_index().rename(columns={"External PK":"Number of Student Offenders"}) # of individual student with at least 1 offense
    group_df_countincidenttype3 = df.groupby("Incident Type").agg({'Pastoral Points':'sum'}) #total quarter points
    #join together
    return (pd.merge(pd.merge(group_df_countincidenttype, group_df_countincidenttype2, on='Incident Type', how='left'),group_df_countincidenttype3,on='Incident Type', how='left')).sort_values(by=["Number of Occurences"],ascending = False)

def applyfilter(df,and_filters):
    filtered_df = df
    for f in and_filters:
        if f is None:
            pass
        elif f[1] in ['All Houses',['Grade 9','Grade 10', 'Grade 11','Grade 12']]:
            pass
        elif f[0]=="Incident Type":
            filtered_df = filtered_df[filtered_df[f[0]]==f[1]]
        elif f[0]=='Grade':
            filtered_df = filtered_df[filtered_df[f[0]].isin(f[1])]
        elif f[0]== 'House':
            filtered_df = filtered_df[filtered_df[f[0]]==f[1]]
        elif f[0]== 'Date':
            filtered_df = filtered_df[(filtered_df[f[0]]<=(f[1][1]))&(filtered_df[f[0]]>=(f[1][0]))]
        elif f[0]=='Student Name':
            filtered_df = filtered_df[filtered_df[f[0]]==f[1]]
        #filtered_df = pd.concat([filtered_df,df[df["Incident Type"]=="filler"]])
    return filtered_df
    
def plt_incidenttype_barchart(df,tab,housefilter = None, gradefilter = None,datefilter=None,studentfilter=None):
    if tab ==1:
        get_df = plt_incident_type_bar1(applyfilter(df,[housefilter,gradefilter,datefilter,studentfilter]))
        fig = px.bar(get_df, x="Incident Type", y=["Pastoral Points","Number of Occurences","Number of Student Offenders"], 
                color_discrete_sequence=['#643843','#85586f','#637A9F'],opacity=1,barmode="overlay",
                title = "Comparing Quarter Counts For each TCS Incident Type: <br>",
                labels={"index": "Incident Type","value": "Count","variable":"Legend"}
               )
    else:
        get_df = plt_incident_type_bar2(applyfilter(df,[housefilter,gradefilter,datefilter,studentfilter]))
        fig = px.bar(get_df, x="Incident Type", y=["Pastoral Points","Number of Occurences"], 
                color_discrete_sequence=['#643843','#85586f','#637A9F'],opacity=1,barmode="overlay",
                title = "Comparing Quarter Counts For each TCS Incident Type: <br>",
                labels={"index": "Incident Type","value": "Count","variable":"Legend"}
               )

    fig.update_layout(xaxis_tickangle=90,
                      hovermode="x unified",
                      #font_family="Verdana", 
                      font_color="black",
                      #title_font_family="Verdana",
                      title_font_color="black",
                      legend_title_font_color="black",
                      title_font_size = 15,
                      title_x = 0.5)
    fig.update_traces(hovertemplate="<br>".join([
                "%{y}<br>"+"<br>",
            ]))#hovertemplate='<b>%{x}</b><br>Number of quarters=%{y}<br>Total Number of offenses=%{y}<br>Number of Individual Offenders =%{y}')

    fig.update_layout(legend=dict(
        y=0.99,
        x=0.99,
        xanchor="right",
        yanchor="top"
    ))
    fig.update_layout(clickmode='event+select')

    return fig 

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = ""
app.css.config.serve_locally = True
server = app.server
app.config.suppress_callback_exceptions = True
clinic_list = merged_df["Incident Type"].unique()
admit_list = merged_df["Student Name"].unique().tolist()
slider_daterange = pd.date_range(start=pd.to_datetime('2023-09-01'),end=pd.to_datetime('2024-06-30'),freq='W')
student_list = np.sort(merged_df["Student Name"].unique().tolist(),axis=0)
student_list_with_house = merged_df[["Student Name","House"]].sort_values("Student Name").drop_duplicates()
qtype_list = merged_df["Incident Type"].unique().tolist()

app.layout = html.Div([
    html.Br(),
    html.H1("Welcome to the TCS Quarter Analytics Dashboard",style = {'color':'#303030', 'textAlign': 'center','font-size':30}),
    dcc.Tabs([
        dcc.Tab(label='All Students/Student Sub-Groups',children = html.Div([description_card(1),
            html.Br(),
            html.Label('Select House(s)',style = {'text-indent':'25px'}),
            dcc.Dropdown(['All Houses','Bethune','Bickle','Brent','Burns','Hodgetts','Ketchum','Orchard','Scott','Rigby','Wright'],id='house_dropdown_tab1',value = "All Houses",optionHeight=25, style={"color": "#3b97c4",
    "font-family": "verdana","font-size":"90%","width": "60%",'margin-left':'12px'}),
    html.Br(),
            html.Label('Select Q Type(s)',style = {'text-indent':'25px'}),
            dcc.Dropdown(['Grade 9', 'Grade 10', 'Grade 11','Grade 12'],value =['Grade 9', 'Grade 10', 'Grade 11','Grade 12'],id = 'grade_dropdown_tab1',multi = True,optionHeight=25,style={"color": "#3b97c4",
    "font-family": "verdana","font-size":"90%","width": "60%",'margin-left':'12px'}),
            html.Br(),
            html.Label('Select Date Range',style={'text-indent':'25px'}),
            dcc.RangeSlider(
                id='dates_slider',
                min = unixTimeMillis(slider_daterange.min()),
                max = unixTimeMillis(slider_daterange.max()),
                value = [unixTimeMillis(slider_daterange.min()),unixTimeMillis(slider_daterange.max())],
                marks = getMarks(slider_daterange),
                tooltip = {"placement": "top","transform": "integertodate"}),
            html.Br(),
            html.Br(),
            html.Div([html.Label('GRAPHICAL VIEWS',style={"color": "#3795FF",
                                                            "font-family": "verdana",
                                                            "font-size":"120%",
                                                            'textAlign': 'center'}),
                    html.Label(id = 'filter_title',style={"color": "#A53FFF",
                                                            "font-family": "verdana",
                                                            "font-size":"95%",
                                                            'textAlign': 'center'}),
                html.Div([
                    dcc.Graph(id = 'incident_type_bar_plot',
                    style={"width":'60%',"height":1000, "margin": 0, 'display': 'inline-block'}
                ),
                html.Div([
                    dcc.Graph(id='click-data_time_scatter_plot', 
                    style={"width":'10%', "height":500,"margin": 0, 'display': 'block'}),
                    dcc.Graph(id='click-data_time_scatter_plot_cumulative', 
                    style={"width":'10%',"height":500,"margin": 0, 'display': 'block'}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"})
                    ])]),
                html.Br(),
                html.Label('RAW PASTORAL REPORT DATA',style={"color": "#3795FF",
                                                            "font-family": "verdana",
                                                            "font-size":"120%",
                                                            'textAlign': 'center'}),
                html.Label(id='filter_title2',style={"color": "#A53FFF",
                                                            "font-family": "verdana",
                                                            "font-size":"95%",
                                                            'textAlign': 'center'}),
                html.Div(id='click-data_incident_types_table')],style={'border':"100px whitesolid"})])),

          dcc.Tab(label = 'Individual Students',children = html.Div(children=[description_card(2),
            html.Br(),
            html.Label('Filter By House',style = {'text-indent':'25px'}),
            dcc.Dropdown(['All Houses','Bethune','Bickle','Brent','Burns','Hodgetts','Ketchum','Orchard','Scott','Rigby','Wright'],id='house_dropdown_tab2',value = "All Houses",optionHeight=25, style={"color": "#3b97c4",
                                                                                                                                                                                                        "font-family": "verdana",
                                                                                                                                                                                                        "font-size":"90%",
                                                                                                                                                                                                        "width": "60%",
                                                                                                                                                                                                        'margin-left':'12px'}),
            html.Br(),
            html.Label('Select Student',style = {'text-indent':'25px'}),
            dcc.Dropdown(student_list,id="student_dropdown_tab2",optionHeight=25, style={"color": "#3b97c4",
                                                                                        "font-family": "verdana",
                                                                                        "font-size":"90%",
                                                                                        "width": "60%",
                                                                                        'margin-left':'12px'}),

            html.Br(),
            html.Label('Select Date Range',style = {'text-indent':'25px'}),
            dcc.RangeSlider(
                id='dates_slider2',
                min = unixTimeMillis(slider_daterange.min()),
                max = unixTimeMillis(slider_daterange.max()),
                value = [unixTimeMillis(slider_daterange.min()),unixTimeMillis(slider_daterange.max())],
                marks = getMarks(slider_daterange),
                tooltip = {"placement": "top","transform": "integertodate"}),
            html.Br(),
            html.Br(),
            html.Div([html.Label('GRAPHICAL VIEWS',style={"color": "#3795FF",
                                                            "font-family": "verdana",
                                                            "font-size":"120%",
                                                            'textAlign': 'center'}),
                    html.Label(id = 'filter_title21',style={"color": "#A53FFF",
                                                            "font-family": "verdana",
                                                            "font-size":"95%",
                                                            'textAlign': 'center'}),
                html.Div([
                    dcc.Graph(id = 'incident_type_bar_plot2',
                    style={"width":'60%', "height":1000,"margin": 0, 'display': 'inline-block'}
                ),
                html.Div([
                    dcc.Graph(id='click-data_time_scatter_plot2', 
                    style={"width":'40%', "height":500,"margin": 0, 'display': 'inline-block'}),
                    dcc.Graph(id='click-data_time_scatter_plot_cumulative2', 
                    style={"width":'40%', "height":500, "margin": 0, 'display': 'inline-block'}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"}),
                    html.Label(".",style={"background-color": "#ffffff","color":"#ffffff"})
                    ])]),
                html.Br(),
                html.Label('RAW PASTORAL REPORT DATA',style={"color": "#3795FF",
                                                            "font-family": "verdana",
                                                            "font-size":"120%",
                                                            'textAlign': 'center'}),
                html.Label(id='filter_title22',style={"color": "#A53FFF",
                                                            "font-family": "verdana",
                                                            "font-size":"95%",
                                                            'textAlign': 'center',
                                                            'background-color':"C2EEFF" }),
                html.Div(id='click-data_incident_types_table2')],style={'border':"100px whitesolid"})]))]),html.Br()
])


@callback(
    Output('incident_type_bar_plot', 'figure'),
    Input('house_dropdown_tab1', 'value'),
    Input('grade_dropdown_tab1', 'value'),
    Input('dates_slider', 'value')) 

def update_incidenttype_barplot(house,grades,dates):
    figure=plt_incidenttype_barchart(merged_df,1,housefilter=("House",house),gradefilter=("Grade",[int(g.split()[1]) for g in grades]),datefilter=("Date",[pd.to_datetime(d,unit='s') for d in dates]))
    return figure


    #'style':{'writing-mode':'vertical-rl', 'text-orientation':'mixed'}

@callback(
    Output('click-data_incident_types_table', 'children'),
    Output('filter_title','children'),
    Output('click-data_time_scatter_plot', 'figure'),
    Output('click-data_time_scatter_plot_cumulative','figure'),
    Output('filter_title2','children'),
    Input('incident_type_bar_plot', 'selectedData'),
    Input('house_dropdown_tab1', 'value'),
    Input('grade_dropdown_tab1', 'value'),
    Input('dates_slider', 'value'),
)
 
def display_click_data(selectedData,house,grades,dates):
    if selectedData is None: 
        filtersdesc = "Showing results  " + (str(house)+" for House , ")*(house!="All Houses") + ("for Grades "+str([int(g.split()[1]) for g in grades])+" , ")*(1<len(grades)<4) + ("for Grade "+str([int(g.split()[1]) for g in grades])+" , ")*(len(grades)==1)+ "from "+ pd.to_datetime(dates[0],unit='s').strftime("%B %d, %Y") + " to " + pd.to_datetime(dates[len(dates)-1],unit='s').strftime("%B %d, %Y") +":"
        df = applyfilter(merged_df,[("House",house),("Grade",[int(g.split()[1]) for g in grades]),("Date",[pd.to_datetime(d,unit='s') for d in dates])])
    elif selectedData is not None:
        filtersdesc =(selectedData["points"][0]["x"]).upper()+"S - "+ "Showing results  " + (str(house)+" for House , ")*(house!="All Houses") + ("for Grades "+str([int(g.split()[1]) for g in grades])+" , ")*(1<len(grades)<4) + ("for Grade "+str([int(g.split()[1]) for g in grades])+" , ")*(len(grades)==1)+ "from "+ pd.to_datetime(dates[0],unit='s').strftime("%B %d, %Y") + " to " + pd.to_datetime(dates[len(dates)-1],unit='s').strftime("%B %d, %Y") +":"
        df = applyfilter(merged_df,[("Incident Type",selectedData["points"][0]["x"]),("House",house),("Grade",[int(g.split()[1]) for g in grades]),("Date",[pd.to_datetime(d,unit='s') for d in dates])])

    #add up pastoral points each day.
    df2 = df[["Date", "Pastoral Points"]].groupby("Date").sum()
    df = pd.merge(df, df2, on='Date', how='left')
    df = df.rename(columns={"Pastoral Points_x":"Pastoral Points"})
    df = df.sort_values("Date")
    df['cumulative_pastoral points'] = df["Pastoral Points"].cumsum()

    df =df.sort_values(["House","Student Name","Date"])[["Date","Student Name","Grade", "House","Incident Type","Pastoral Points","Details", "cumulative_pastoral points"]]
    df["Date"] = [d.date() for d in df["Date"]]
    df["Student's Offence Count"] = df.groupby('Student Name')['Student Name'].transform('size')
    table = html.Div([dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
    hidden_columns=['cumulative_pastoral points'],
    sort_action="native",
    css=[{"selector": ".show-hide", "rule": "display: none"}],
    sort_mode="multi",
    style_cell={
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
        'minWidth': 130,
        'maxWidth': 700,
        'whiteSpace':'normal'
    },
    style_table={
        'overflowY': 'scroll',
        'maxHeight': '800px',
        'columnSize':"autoSize",
        'column_size_options': {
        'keys':["details"],
        'skipHeader': False
    }
        },
    fixed_rows={'headers': True},
    tooltip_data=[
    {
        column: {'value': str(value), 'type': 'markdown'}
        for column, value in row.items()
    } for row in df.to_dict('records')
    ],tooltip_duration=None)],style={'max_width': 100})

    #if table is None:
       # return [None,None]
    
    df_temp2 = df

    df_temp = df_temp2.sort_values("Date")
    df_temp2 = (df_temp2[["Date", 'cumulative_pastoral points']].groupby(["Date"]).min()).reset_index()

    time_fig1 = px.scatter(df_temp, x="Date", y="Pastoral Points",color_discrete_sequence=['#6e0b2a'],title="Pastoral Points Assigned Over Time<br>")
    time_fig1.update_traces(hovertemplate="<br>".join([
            "%{x}<br>%{y}<br>",
        ]))
    time_fig1.update_layout(
                    font_family='verdana', 
                    font_color="black",
                    title_font_family="Verdana",
                    title_font_color="black",
                    title_font_size = 16,
                    title_x = 0.5)

    time_fig2 = px.line(df_temp2,x="Date",y='cumulative_pastoral points',title="Accumulation of Pastoral Points Over Time<br>",line_shape='hv')
    time_fig2.update_traces(hovertemplate="<br>".join([
            "%{y}<br>",
        ]))
    time_fig2.update_layout(
                    yaxis={"title": "Cumulative Pastoral Points"},
                    hovermode="x unified",
                    font_family="Verdana", 
                    font_color="black",
                    title_font_family="Verdana",
                    title_font_color="black",
                    title_font_size = 16,
                    title_x = 0.5)
                        
    return [table,filtersdesc,time_fig1,time_fig2,filtersdesc]

"""TAB 2 CALLBACK FUNCTIONS"""

@callback(
    Output('student_dropdown_tab2', 'options'),
    Input('house_dropdown_tab2', 'value'))

def update_student_dropdown(house_dropdown_data):
    if house_dropdown_data == "All Houses": #list all students
        return student_list
    else: #filter by house 
        student_list_with_house_filtered = student_list_with_house[student_list_with_house["House"]==house_dropdown_data]
        return (student_list_with_house_filtered["Student Name"].tolist())

@callback(
    Output('incident_type_bar_plot2', 'figure'),
    Input('student_dropdown_tab2', 'value'),
    Input('dates_slider2', 'value')) 

def update_incidenttype_barplot_tab2(student,dates):
    figure=plt_incidenttype_barchart(merged_df,2,datefilter=("Date",[pd.to_datetime(d,unit='s') for d in dates]),studentfilter=("Student Name",student))
    return figure

"""TAB 2 CALLBACK FUNCTIONS"""

@callback(
    Output('click-data_incident_types_table2', 'children'),
    Output('filter_title21','children'),
    Output('click-data_time_scatter_plot2', 'figure'),
    Output('click-data_time_scatter_plot_cumulative2','figure'),
    Output('filter_title22','children'),
    Input('incident_type_bar_plot2', 'selectedData'),
    Input('student_dropdown_tab2', 'value'),
    Input('dates_slider2', 'value'),
)
 
def display_click_data_tab2(selectedData,student,dates):
    if selectedData is None: 
        if student is None or student=="": 
            filtersdesc = "Please SELECT A STUDENT using the dropdown box above."#"Showing results  " + "from "+ pd.to_datetime(dates[0],unit='s').strftime("%B %d, %Y") + " to " + pd.to_datetime(dates[len(dates)-1],unit='s').strftime("%B %d, %Y") +":"
        else:
            student_fname = student.split(",")[1]
            student_lname = student.split(",")[0]
            filtersdesc = "Showing results for " + student_fname + " " + student_lname + " from "+ pd.to_datetime(dates[0],unit='s').strftime("%B %d, %Y") + " to " + pd.to_datetime(dates[len(dates)-1],unit='s').strftime("%B %d, %Y") +":"
        df = applyfilter(merged_df,[("Student Name",student),("Date",[pd.to_datetime(d,unit='s') for d in dates])])
    elif selectedData is not None:
        student_fname = student.split(",")[1]
        student_lname = student.split(",")[0]
        filtersdesc =(selectedData["points"][0]["x"]).upper()+"S - "+ "Showing results for " + student_fname + " " + student_lname + " from "+ pd.to_datetime(dates[0],unit='s').strftime("%B %d, %Y") + " to " + pd.to_datetime(dates[len(dates)-1],unit='s').strftime("%B %d, %Y") +":"
        df = applyfilter(merged_df,[("Incident Type",selectedData["points"][0]["x"]),("Student Name",student),("Date",[pd.to_datetime(d,unit='s') for d in dates])])

    #add up pastoral points each day.
    df2 = df[["Date", "Pastoral Points"]].groupby("Date").sum()
    df = pd.merge(df, df2, on='Date', how='left')
    df = df.rename(columns={"Pastoral Points_x":"Pastoral Points"})
    df = df.sort_values("Date")
    df['cumulative_pastoral points'] = df["Pastoral Points"].cumsum()

    df =df.sort_values(["House","Student Name","Date"])[["Date","Student Name","Grade", "House","Incident Type","Pastoral Points","Details", "cumulative_pastoral points"]]
    df["Date"] = [d.date() for d in df["Date"]]
    df["Student's Offence Count"] = df.groupby('Student Name')['Student Name'].transform('size')
    table = html.Div([dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], 
    hidden_columns=['cumulative_pastoral points'],
    sort_action="native",
    css=[{"selector": ".show-hide", "rule": "display: none"}],
    sort_mode="multi",
    style_cell={
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
        'minWidth': 130,
        'maxWidth': 700,
        'whiteSpace':'normal'
    },
    style_table={
        'overflowY': 'scroll',
        'maxHeight': '800px',
        'columnSize':"autoSize",
        'column_size_options': {
        'keys':["details"],
        'skipHeader': False
    }
        },
    fixed_rows={'headers': True},
    tooltip_data=[
    {
        column: {'value': str(value), 'type': 'markdown'}
        for column, value in row.items()
    } for row in df.to_dict('records')
    ],tooltip_duration=None)],style={'max_width': 100})

    #if table is None:
       # return [None,None]
    
    df_temp2 = df

    df_temp = df_temp2.sort_values("Date")
    df_temp2 = (df_temp2[["Date", 'cumulative_pastoral points']].groupby(["Date"]).min()).reset_index()
    time_fig1 = px.scatter(df_temp, x="Date", y="Pastoral Points",color_discrete_sequence=['#6e0b2a'],title="Pastoral Points Assigned Over Time<br>")
    time_fig1.update_traces(hovertemplate="<br>".join([
            "%{x}<br>%{y}<br>",
        ]))
    time_fig1.update_layout(
                    font_family="Verdana", 
                    font_color="black",
                    title_font_family="Verdana",
                    title_font_color="black",
                    title_font_size = 16,
                    title_x = 0.5)

    time_fig2 = px.line(df_temp2,x="Date",y='cumulative_pastoral points',title="Accumulation of Pastoral Points Over Time<br>",line_shape='hv')
    time_fig2.update_traces(hovertemplate="<br>".join([
            "%{y}<br>",
        ]))
    time_fig2.update_layout(
                    yaxis={"title": "Cumulative Pastoral Points"},
                    hovermode="x unified",
                    font_family="Verdana", 
                    font_color="black",
                    title_font_family="Verdana",
                    title_font_color="black",
                    title_font_size = 16,
                    title_x = 0.5)
                        
    return [table,filtersdesc,time_fig1,time_fig2,filtersdesc]

if __name__ == '__main__':
    app.run(debug=True,port=8050)
