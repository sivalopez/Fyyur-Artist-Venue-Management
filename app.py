#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from sqlalchemy.dialects import postgresql
from sqlalchemy import func, DateTime
from datetime import datetime
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

# connect to a local postgresql database
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(postgresql.ARRAY(db.String(120)), nullable=False)
    website = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String)
    artists = db.relationship('Artist', secondary='show', backref=db.backref('venues', lazy=True))

    def __repr__(self):
      return (
        f'<Venue id: {self.id}, name: {self.name}, city: {self.city}'
        f', state: {self.state}, address: {self.address}, phone: {self.phone}'
        f', image_link: {self.image_link}, facebook_link: {self.facebook_link}'
        f', genres: {self.genres}, website: {self.website}, seeking_talent: {self.seeking_talent}'
        f', seeking_description: {self.seeking_description}>\n'
      )

class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(postgresql.ARRAY(db.String(120)), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String)

    def __repr__(self):
      return (
        f'<Artist id: {self.id}, name: {self.name}, city: {self.city}'
        f', state: {self.state}, phone: {self.phone}'
        f', image_link: {self.image_link}, facebook_link: {self.facebook_link}'
        f', genres: {self.genres}, website: {self.website}, seeking_venue: {self.seeking_venue}'
        f', seeking_description: {self.seeking_description}>'
      )

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.
class Show(db.Model):
    __tabelname__ = 'show'

    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), primary_key=True)
    start_time = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
      return (
        f'<Show artist_id: {self.artist_id}, venue_id: {self.venue_id}, start_time: {self.start_time}>'
      )

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  current_time = datetime.now()
  
  dbData = []
  try:
    cityStateGroup = Venue.query.with_entities(Venue.id, Venue.city, Venue.state)\
      .distinct(Venue.city, Venue.state).order_by(Venue.state, Venue.city).all()

    for area in cityStateGroup:
      venues = []
      areaVenues = Venue.query.filter_by(state=area.state).filter_by(city=area.city).all()
      for venue in areaVenues:
        num_upcoming_shows = Show.query.with_entities(func.count(Show.venue_id))\
          .filter_by(venue_id=area.id).filter(Show.start_time>current_time).first()

        venueData = {
          "id": venue.id,
          "name": venue.name,
          "num_upcoming_shows": num_upcoming_shows[0]
        }
        venues.append(venueData)

      areaVenue = {
        "city": area.city,
        "state": area.state,
        "venues": venues
      }
      dbData.append(areaVenue)
    
  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  # data=[{
  #   "city": "San Francisco",
  #   "state": "CA",
  #   "venues": [{
  #     "id": 1,
  #     "name": "The Musical Hop",
  #     "num_upcoming_shows": 0,
  #   }, {
  #     "id": 3,
  #     "name": "Park Square Live Music & Coffee",
  #     "num_upcoming_shows": 1,
  #   }]
  # }, {
  #   "city": "New York",
  #   "state": "NY",
  #   "venues": [{
  #     "id": 2,
  #     "name": "The Dueling Pianos Bar",
  #     "num_upcoming_shows": 0,
  #   }]
  # }]
  return render_template('pages/venues.html', areas=dbData);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  try:
    current_time = datetime.now()
    search_term = request.form.get('search_term','')
    venues = Venue.query.filter(Venue.name.ilike('%' + search_term + '%')).all()
    error = False
    response = {}

    if venues:
      data = []
      for venue in venues:
        num_upcoming_shows = len(Venue.query.join(Show).with_entities(Venue.id, Show.start_time)\
          .filter(Show.venue_id==venue.id).filter(Show.start_time>current_time).all())
        data.append({
          "id": venue.id,
          "name": venue.name,
          "num_upcoming_shows": num_upcoming_shows  
        })
      
      response = {
        "count": len(venues),
        "data": data
      }
    else:
      error = True
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('Could not find results for \"' + request.form.get('search_term', '') + '\"')
    return redirect(url_for('venues'))
  else:
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # Replace with real venue data from the venues table, using venue_id
  
  current_time = datetime.now()
  error = False
  dbData = {}

  try:
    venue = Venue.query.filter_by(id=venue_id).first()
    if venue is None:
      error = True
    else: 
      past_shows = []
      upcoming_shows = []
      past_shows_count = 0 
      upcoming_shows_count = 0

      # Collecting past shows
      pastShows = Show.query.join(Artist).with_entities(Artist.id, Artist.name, Artist.image_link, Show.start_time)\
        .filter(Show.venue_id==venue.id).filter(Show.start_time<current_time).all()
      
      if pastShows:
        past_shows_count = len(pastShows)
        for show in pastShows:
          pastShowObj = {
            "artist_id": show.id,
            "artist_name": show.name,
            "artist_image_link": show.image_link,
            "start_time": format_datetime(str(show.start_time))
          }
          past_shows.append(pastShowObj)

      # Collecting upcoming shows
      upcomingShows = Show.query.join(Artist).with_entities(Artist.id, Artist.name, Artist.image_link, Show.start_time)\
        .filter(Show.venue_id==venue.id).filter(Show.start_time>current_time).all()
      if upcomingShows:
        upcoming_shows_count = len(upcomingShows)
        for show in upcomingShows:
          upcomingShowObj = {
            "artist_id": show.id,
            "artist_name": show.name,
            "artist_image_link": show.image_link,
            "start_time": format_datetime(str(show.start_time))
          }
          upcoming_shows.append(upcomingShowObj)

      dbData = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": past_shows_count,
        "upcoming_shows_count": upcoming_shows_count
      }

  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    abort(404)
  else:
    return render_template('pages/show_venue.html', venue=dbData)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  data = {}
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    # Setting default value when getting request parameter value.
    phone = request.form.get('phone','')
    genres = request.form.getlist('genres')
    website = request.form['website']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    # Setting default values when getting the request parameter value.
    # Check value and convert to correct boolean value of True or False.
    seeking_talent = True if request.form.get('seeking_talent', 'n') == 'y' else False
    seeking_description = request.form.get('seeking_description', '')

    data['venue_name'] = name

    # insert form data as a new Venue record in the db, instead
    venue = Venue(name=name,city=city, state=state, address=address, phone=phone, \
      genres=genres, website=website, image_link=image_link, facebook_link=facebook_link, \
      seeking_talent=seeking_talent, seeking_description=seeking_description)
    print(venue)

    # Insert into db and commit.
    db.session.add(venue)
    db.session.commit()

    # modify data to be the data object returned from db insertion
    data['venue_id'] = venue.id

  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    # On unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    flash('An error occurred. Venue \'' + data['venue_name'] + '\' could not be listed.')
  else:
    # on successful db insert, flash success
    flash('Venue \'' + data['venue_name'] + '\' was successfully listed!')

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # Replace with real data returned from querying the database
  dbData = []

  try:
    artists = Artist.query.all()
    if artists:
      for artist in artists:
        artistObj = {
          "id": artist.id,
          "name": artist.name
        }
        dbData.append(artistObj)
  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  return render_template('pages/artists.html', artists=dbData)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # Implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  try:
    current_time = datetime.now()
    search_term = request.form.get('search_term','')
    artists = Artist.query.filter(Artist.name.ilike('%' + search_term + '%')).all()
    error = False

    response = {}
    if artists:
      data = []
      for artist in artists:
        num_upcoming_shows = len(Artist.query.join(Show).with_entities(Artist.id, Show.start_time)\
          .filter(Show.artist_id==artist.id).filter(Show.start_time>current_time).all())
        data.append({
          "id": artist.id,
          "name": artist.name,
          "num_upcoming_shows": num_upcoming_shows
        })
      response = {
        "count": len(artists),
        "data": data
      }
    else:
      error = True
  except:
    error = True
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()

  if error:
    flash('Could not find results for \"' + request.form.get('search_term', '') + '\"')
    return redirect(url_for('artists'))
  else:
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  # Replace with real venue data from the venues table, using venue_id
  current_time = datetime.now()
  error = False

  dbData = {}
  try:
    artist = Artist.query.filter_by(id=artist_id).first()
    if artist is None:
      error = True
    else:
      past_shows = []
      past_shows_count = 0
      upcoming_shows = []
      upcoming_shows_count = 0

      # Collecting past shows
      pastShows = Show.query.join(Venue).with_entities(Venue.id, Venue.name, Venue.image_link, Show.start_time)\
        .filter(Show.artist_id==artist_id).filter(Show.start_time<current_time).all()

      if pastShows:
        past_shows_count = len(pastShows)
        for show in pastShows:
          pastShowObj = {
            "venue_id": show.id,
            "venue_name": show.name,
            "venue_image_link": show.image_link,
            "start_time": format_datetime(str(show.start_time))
          }
          past_shows.append(pastShowObj)

      # Collecting upcoming shows
      upcomingShows = Show.query.join(Venue).with_entities(Venue.id, Venue.name, Venue.image_link, Show.start_time)\
        .filter(Show.artist_id==artist_id).filter(Show.start_time>current_time).all()

      if upcomingShows:
        upcoming_shows_count = len(upcomingShows)
        for show in upcomingShows:
          upcomingShowObj = {
            "venue_id": show.id,
            "venue_name": show.name,
            "venue_image_link": show.image_link,
            "start_time": format_datetime(str(show.start_time))
          }
          upcoming_shows.append(upcomingShowObj)

      dbData = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": past_shows_count,
        "upcoming_shows_count": upcoming_shows_count
      }

  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    abort(404)
  else:
    return render_template('pages/show_artist.html', artist=dbData)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  error = False
  data = {}
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form.get('phone','')
    genres = request.form.getlist('genres')
    image_link = request.form.get('image_link','')
    facebook_link = request.form.get('facebook_link','')
    website = request.form.get('website','')
    seeking_venue = True if request.form.get('seeking_venue', 'n') == 'y' else False
    seeking_description = request.form.get('seeking_description','')

    # Insert form data as a new Artist record in the db, instead
    artist = Artist(name=name, city=city, state=state, phone=phone, genres=genres, \
      image_link=image_link, facebook_link=facebook_link, website=website, \
        seeking_venue=seeking_venue, seeking_description=seeking_description)
    print(artist)
    data['name'] = name

    db.session.add(artist)
    db.session.commit()
    data['artist_id'] = artist.id

    # TODO: modify data to be the data object returned from db insertion
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  
  # On unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  if error: 
    flash('An error occurred. Artist \'' + data['name'] + '\' could not be listed.')
  else: 
    # on successful db insert, flash success
    flash('Artist \'' + data['name'] + '\' was successfully listed!')
 
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  dbData = []

  try:
    shows = Show.query.join(Venue).join(Artist).with_entities(Show.venue_id, Venue.name.label('venue_name'), Show.artist_id, Artist.name, Artist.image_link, Show.start_time).all()

    for show in shows:
      showObj = {
        "venue_id": show.venue_id,
        "venue_name": show.venue_name,
        "artist_id": show.artist_id,
        "artist_name": show.name,
        "artist_image_link": show.image_link,
        "start_time": format_datetime(str(show.start_time))
      }
      dbData.append(showObj)
  except:
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  # data=[{
  #   "venue_id": 1,
  #   "venue_name": "The Musical Hop",
  #   "artist_id": 4,
  #   "artist_name": "Guns N Petals",
  #   "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
  #   "start_time": "2019-05-21T21:30:00.000Z"
  # }, {
  #   "venue_id": 3,
  #   "venue_name": "Park Square Live Music & Coffee",
  #   "artist_id": 5,
  #   "artist_name": "Matt Quevedo",
  #   "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
  #   "start_time": "2019-06-15T23:00:00.000Z"
  # }, {
  #   "venue_id": 3,
  #   "venue_name": "Park Square Live Music & Coffee",
  #   "artist_id": 6,
  #   "artist_name": "The Wild Sax Band",
  #   "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
  #   "start_time": "2035-04-01T20:00:00.000Z"
  # }, {
  #   "venue_id": 3,
  #   "venue_name": "Park Square Live Music & Coffee",
  #   "artist_id": 6,
  #   "artist_name": "The Wild Sax Band",
  #   "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
  #   "start_time": "2035-04-08T20:00:00.000Z"
  # }, {
  #   "venue_id": 3,
  #   "venue_name": "Park Square Live Music & Coffee",
  #   "artist_id": 6,
  #   "artist_name": "The Wild Sax Band",
  #   "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
  #   "start_time": "2035-04-15T20:00:00.000Z"
  # }]
  return render_template('pages/shows.html', shows=dbData)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False
  try:
    artist_id = request.form.get('artist_id')
    venue_id = request.form.get('venue_id')
    start_time = request.form.get('start_time')

    show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
    print("SL printing show: " + str(show))
    # TODO: insert form data as a new Show record in the db, instead
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    # TODO: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Show could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    flash('An error occurred. Show could not be listed.')
  else:
    # on successful db insert, flash success
    flash('Show was successfully listed!')

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
