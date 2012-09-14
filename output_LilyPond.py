#! /usr/bin/python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         outputLilypond.py
# Purpose:      Outputs music21 Objects into LilyPond Format
#
# Copyright (C) 2012 Christopher Antila
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------



## Import:
# python standard library
import os # needed for writing the output file
from subprocess import Popen, PIPE # for running bash things
from string import letters as string_letters
from random import choice as random_choice
# music21
from music21 import note, clef, meter, key, stream, instrument, \
   metadata, layout, bar, humdrum, duration
from music21.duration import DurationException
# vis
from file_output import file_outputter



#-------------------------------------------------------------------------------
class UnidentifiedObjectError( Exception ):
   '''
   When something can't be identified.
   '''
   def __init__( self, val ):
      self.value = val
   def __str__( self ):
      return repr( self.value )
#-------------------------------------------------------------------------------



#-------------------------------------------------------------------------------
class ImpossibleToProcessError( Exception ):
   '''
   When something is identified, but for some reason cannot be processed.
   '''
   def __init__( self, val ):
      self.value = val
   def __str__( self ):
      return repr( self.value )
#-------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def string_of_n_letters( n ):
   '''
   Generates a string of n random letters.
   '''
   post = ""
   for i in xrange(n):
      post += random_choice( string_letters )
   return post
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def octave_num_to_lily( num ):
   '''
   Returns the LilyPond symbol corresponding to the octave number.
   '''

   dictionary_of_octaves = { 0:",,,", 1:",,", 2:",", 3:"", 4:"'", 5:"''", \
      6:"'''", 7:"''''", 8:"'''''", 9:"''''''", 10:"'''''''", 11:"''''''''", \
      12:"'''''''''" }

   if num in dictionary_of_octaves:
      return dictionary_of_octaves[num]
   else:
      raise UnidentifiedObjectError( 'Octave out of range: ' + str(num) )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def pitch_to_lily( p, include_octave = True ):
   '''
   Returns a str that is the LilyPond pitch name for the pitch.Pitch

   Second argument can be set to 'no' to avoid the commas or apostrophes that
   indicate octave.
   '''
   pc = p.name.lower()
   post = pc[0]
   for accidental in pc[1:]:
      if '-' == accidental:
         post += 'es'
      elif '#' == accidental:
         post += 'is'

   if include_octave:
      if p.octave is None:
         post += octave_num_to_lily( p.implicitOctave )
      else:
         post += octave_num_to_lily( p.octave )

   return post
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def duration_to_lily( dur, known_tuplet = False ): # "dur" means "duration"
   '''
   Returns a LilyPond length integer (like '4' for quarter note) corresponding
   to the Duration passed in.
   '''
   # TODO: We should be able to deal with multiple-component durations that are
   # actually from a single Note/Rest... as with the duration of a Measure. For
   # this I imagine we would need to round.

   # First of all, we can't deal with tuplets or multiple-component durations
   # in this method. We need process_measure() to help.
   if dur.tuplets is not ():
      # We know either there are multiple components or we have part of a
      # tuplet, we we need to find out which.
      if len(dur.components) > 1:
         # We have multiple components
         raise ImpossibleToProcessError( 'Cannot process durations with ' + \
            'multiple components (received ' + str(dur.components) + \
            ' for quarterLength of ' + str(dur.quarterLength) + ')' )
      elif known_tuplet:
         # We have part of a tuple. This isn't necessarily a problem; we'll
         # assume we are given this by process_measure() and that it knows
         # what's going on. But, in tuplets, the quarterLength doesn't match
         # the type of written note, so we'll make a new Duration with an
         # adjusted quarterLength
         dur = duration.Duration( dur.type )
      else:
         raise ImpossibleToProcessError( 'duration_to_lily(): Cannot process tuplet components' )

   # We need both a list of our potential durations and a dictionary of what
   # they mean in LilyPond terms.
   list_of_durations = [16.0, 8.0, 4.0, 2.0, 1.0, 0.5,  0.25, 0.125, 0.0625, \
      0.03125]
   dictionary_of_durations = { 16.0:'\longa', 8.0:'\\breve', 4.0:'1', 2.0:'2', \
      1.0:'4', 0.5:'8', 0.25:'16', 0.125:'32', 0.0625:'64', 0.3125:'128' }

   # So we only access the quarterLength once
   dur_qL = dur.quarterLength

   # If there are no dots, the value should be in the dictionary, and we can
   # simply return it.
   if dur_qL in dictionary_of_durations:
      return dictionary_of_durations[dur_qL]
   else:
      # We have to figure out the largest value that will fit, then append the
      # correct number of dots.
      post = ''
      for d in list_of_durations:
         if (dur_qL - d) > 0.0:
            post += dictionary_of_durations[d]
            break

      for i in xrange(dur.dots):
         post += "."

      return post
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def note_to_lily( lily_this, known_tuplet = False ):
   '''
   Returns a str that is a LilyPond representation of the inputted note.Note.

   Additionally appends any value in the Note object's "lily_markup" property.

   The second argument, known_tuplet, is not used by note_to_lily() but passed
   on to duration_to_lily().
   '''

   post = ''

   if len(lily_this.duration.components) > 1:
      the_pitch = pitch_to_lily( lily_this.pitch )
      for durational_component in lily_this.duration.components:
         post += the_pitch + duration_to_lily( durational_component, known_tuplet ) + '~ '
      post = post[:-2]
   elif lily_this.isRest:
      post += "r" + duration_to_lily( lily_this.duration, known_tuplet )
   else:
      post += pitch_to_lily( lily_this.pitch ) + duration_to_lily( lily_this.duration, known_tuplet )

   if lily_this.tie is not None:
      if lily_this.tie.type is 'start':
         post += "~"

   if hasattr( lily_this, 'lily_markup' ):
      post += str(lily_this.lily_markup)

   return post
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def barline_to_lily( bl ):
   '''
   Given a music21.bar.Barline object, will return a str that has the LilyPond
   representation of that barline.
   '''
   # From the music21 source code... a list of barline styles...
   #
   # barStyleList = ['regular', 'dotted', 'dashed', 'heavy', 'double', 'final',
   #               'heavy-light', 'heavy-heavy', 'tick', 'short', 'none']

   dictionary_of_barlines = { 'regular':"|", 'dotted':":", 'dashed':"dashed", \
      'heavy':"|.|", 'double':"||", 'final':"|.", 'heavy-light':".|", \
      'heavy-heavy':".|.", 'tick':"'", 'short':"'", 'none':"" }

   post = '\\bar "'

   if bl.style in dictionary_of_barlines:
      post += dictionary_of_barlines[bl.style] + '"'
      return post
   else:
      UnidentifiedObjectError( 'Barline type not recognized (' + bl.style + ')' )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def process_measure( the_meas ):
   '''
   Returns a str that is one line of a LilyPond score, containing one Measure.

   Input should be a Measure.
   '''

   post = "\t"

   # Hold whether this Measure is supposed to be "invisible"
   invisible = False
   if hasattr( the_meas, 'lily_invisible' ):
      invisible = the_meas.lily_invisible

   # Add the first requirement of invisibility
   if invisible:
      post += '\stopStaff\n\t'

   # first check if it's a partial (pick-up) measure
   if 0.0 < the_meas.duration.quarterLength < the_meas.barDuration.quarterLength:
      #print( str(the_meas.duration.quarterLength) + ' andza ' + str(the_meas.barDuration.quarterLength) )
      # NOTE: This next check could have been done in the first place, but it's
      # a work-around for what I think is a bug, so I didn't.
      if round( the_meas.duration.quarterLength, 2 ) < the_meas.barDuration.quarterLength:
         # But still, we may get something stupid...
         try:
            post += "\\partial " + duration_to_lily( the_meas.duration ) + "\n\t"
         except UnidentifiedObjectError as uoe:
            # ... so if it doesn't work the first time, it may in fact be a
            # partial measure; we'll try rounding and see what we can get.
            rounded_duration = duration.Duration( round( the_meas.duration.quarterLength, 2 ) )
            post += "\\partial " + duration_to_lily( rounded_duration ) + "\n\t"

   # Make the_meas an iterable, so we can pull in multiple elements when we
   # need to deal with tuplets.
   the_meas = iter( the_meas )

   # now fill in all the stuff
   for obj in the_meas:
      # Note or Rest
      if isinstance( obj, note.Note ) or isinstance( obj, note.Rest ):
         # TODO: is there a situation where I'll ever need to deal with
         # multiple-component durations for a single Note/Rest?
         # ANSWER: yes, sometimes

         # Is it a full-measure rest?
         if isinstance( obj, note.Rest) and \
            the_meas.srcStream.barDuration.quarterLength == obj.quarterLength:
               if invisible:
                  post += 's' + duration_to_lily( obj.duration ) + ' '
               else:
                  post += 'R' + duration_to_lily( obj.duration ) + ' '
         # Is it the start of a tuplet?
         elif obj.duration.tuplets is not None and len(obj.duration.tuplets) > 0:
            #print( str( obj.duration.tuplets) )
            #if obj.duration.tuplets != ():
            #if len(obj.duration.tuplets) > 0:
               number_of_tuplet_components = obj.duration.tuplets[0].numberNotesActual
               in_the_space_of = obj.duration.tuplets[0].numberNotesNormal
               post += '\\times ' + str(in_the_space_of) + '/' + \
                  str(number_of_tuplet_components) + ' { ' + note_to_lily( obj, True ) + " "
               for tuplet_component in xrange( number_of_tuplet_components - 1 ):
                  post += note_to_lily( next(the_meas), True ) + " "
               post += '} '
         # It's just a regular note or rest
         else:
            post += note_to_lily( obj ) + " "

      #if isinstance( obj, note.Note ):
         #post += note_to_lily( obj ) + " "
      #elif isinstance( obj, note.Rest ):
         ## If it's a full-measure rest, we'll use the upper-case symbol so
         ## the rest is placed in the middle of the bar. This is something
         ## note_to_lily() couldn't pick up without access to the_meas
         #if the_meas.barDuration.quarterLength == obj.quarterLength:
            #post += 'R' + duration_to_lily( obj.duration ) + ' '
         #else:
            #post += note_to_lily( obj ) + " "
      # Clef
      elif isinstance( obj, clef.Clef ):
         if isinstance( obj, clef.TrebleClef ):
            post += "\\clef treble\n\t"
         elif isinstance( obj, clef.BassClef ):
            post += "\\clef bass\n\t"
         elif isinstance( obj, clef.TenorClef ):
            post += "\\clef tenor\n\t"
         elif isinstance( obj, clef.AltoClef ):
            post += "\\clef alto\n\t"
         else:
            raise UnidentifiedObjectError( 'Clef type not recognized: ' + obj )
      # Time Signature
      elif isinstance( obj, meter.TimeSignature ):
         post += "\\time " + str(obj.beatCount) + "/" + str(obj.denominator) + "\n\t"
      # Key Signature
      elif isinstance( obj, key.KeySignature ):
         pm = obj.pitchAndMode
         if 2 == len(pm) and pm[1] is not None:
            post += "\\key " + pitch_to_lily( pm[0], include_octave=False ) + " \\" + pm[1] + "\n\t"
         else:
            # We'll have to assume it's \major, because music21 does that.
            post += "\\key " + pitch_to_lily( pm[0], include_octave=False ) + " \\major\n\t"
      # Barline
      elif isinstance( obj, bar.Barline ):
         # There's no need to write down a regular barline, because they tend
         # to happen by themselves. Of course, this will have to change once
         # we have the ability to override the standard barline.
         if 'regular' != obj.style:
            post += barline_to_lily( obj ) + " "
      # PageLayout and SystemLayout
      elif isinstance( obj, layout.SystemLayout ) or isinstance( obj, layout.PageLayout ):
         # I don't know what to do with these undocumented features.
         pass
      # **kern importer garbage... well, it's only garbage to us
      elif isinstance( obj, humdrum.spineParser.MiscTandem ):
         # http://mit.edu/music21/doc/html/moduleHumdrumSpineParser.html
         # Is there really nothing we can use this for? Seems like these
         # exist only to help music21 developers.
         pass
      # We don't know what it is, and should probably figure out!
      else:
         raise UnidentifiedObjectError( 'Unknown object in Bar: ' + str(obj) )
   #----

   # Append a bar-check symbol, if there was anything outputted.
   if len(post) > 1:
      post += "|\n"

   # The final requirement of invisibility
   if invisible:
      post += '\t\\startStaff\n'

   return post
# End process_measure() -------------------------------------------------------



#------------------------------------------------------------------------------
def process_analysis_voice( a_v ):
   '''
   Processes an analysis voice from vis. This method can't deal with tuplets,
   though it will eventually need to.
   '''

   # Helper method stolen from note_to_lily()
   def space_for_lily( lily_this ):
      post = 's'

      # DEBUG
      #print( '--- got analysis voice thing at offset ' + str(lily_this.offset) )
      # END DEBUG

      if len(lily_this.duration.components) > 1:
         for durational_component in lily_this.duration.components:
            post += duration_to_lily( durational_component ) + '~ '
         post = post[:-2]
      else:
         post += duration_to_lily( lily_this.duration )

      if lily_this.tie is not None:
         if lily_this.tie.type is 'start':
            post += "~"

      if hasattr( lily_this, 'lily_markup' ):
         post += str(lily_this.lily_markup)

      return post

   # Just try to fill in all the stuff
   post = ''

   for obj in a_v:
      post += '\t' + space_for_lily( obj ) + '\n'

   return post
# End process_analysis_voice() ------------------------------------------------



#------------------------------------------------------------------------------
def process_stream( s, the_settings ):
   '''
   Outputs a str containing part or all of a LilyPond source file, when given
   a stream.*

   So far, can be called with:
   - stream.Part
   - stream.Score
   - metadata.Metadata
   - layout.StaffGroup

   The second argument is a LilyPond_Settings object.

   Note that if a stream.Part has the attribute 'lily_analysis_voice' and it is
   set to True, then all Note objects will be turned into spacer objects that
   contain an annotation, and all Rest objects will be turned into spacer
   objects that do not contain an annotation.
   '''
   post = ""
   # Score ------------------------------------------------
   if isinstance( s, stream.Score ):
      # Things Before Parts
      # Our mark!
      post = '% LilyPond output from music21 via "output_LilyPond.py"\n'
      # Version
      post += '\\version "' + \
         the_settings.get_property( 'lilypond_version' ) + \
         '"\n\n'
      # Set paper size
      post += '\\paper {\n\t#(set-paper-size "' + \
         the_settings.get_property( 'paper_size' ) + \
         '")\n}\n\n'

      # Parts
      # This can hold all of our parts... they might also be a StaffGroup,
      # a Metadata object, or something else.
      list_of_parts = []
      # Go through the possible parts and see what we find.
      for possible_part in s:
         list_of_parts.append( process_stream( possible_part, the_settings ) + "\n" )
      # Append the parts to the score we're building. In the future, it'll
      # be important to re-arrange the parts if necessary, or maybe to filter
      # things, so we'll keep everything in this supposedly efficient loop.
      for i in xrange(len(list_of_parts)):
         post += list_of_parts[i]

      # Things After Parts
      # Output the \score{} block
      post += '\\score {\n\t\\new StaffGroup\n\t<<\n'
      for each_part in the_settings._partsInThisScore:
         if each_part in the_settings._analysis_notation_parts:
            post += '\t\t\\new VisAnnotation = "' + each_part + '" \\' + each_part + '\n'
         else:
            post += '\t\t\\new Staff = "' + each_part + '" \\' + each_part + '\n'
      post += '\t>>\n'
      # Output the \layout{} block
      post += '\t\\layout{\n'
      if the_settings.get_property( 'indent' ) is not None:
         post += '\t\tindent = ' + the_settings.get_property( 'indent' ) + '\n'
      post += '''\t\t% VisAnnotation Context
\t\t\context
\t\t{
\t\t\t\\type "Engraver_group"
\t\t\t\\name VisAnnotation
\t\t\t\\alias Voice
\t\t\t\consists "Output_property_engraver"
\t\t\t\consists "Script_engraver"
\t\t\t\consists "Text_engraver"
\t\t\t\consists "Skip_event_swallow_translator"
\t\t\t\consists "Axis_group_engraver"
\t\t}
\t\t% End VisAnnotation Context
\t\t
\t\t% Modify "StaffGroup" context to accept VisAnnotation context.
\t\t\context
\t\t{
\t\t\t\StaffGroup
\t\t\t\\accepts VisAnnotation
\t\t}
'''
      post += '\t}\n}\n'

   # Part -------------------------------------------------
   elif isinstance( s, stream.Part ):
      # Start the Part
      # We used to use some of the part's .bestName, but many scores (like
      # for **kern) don't have this.
      callThisPart = string_of_n_letters( 8 )
      the_settings._partsInThisScore.append( callThisPart )
      post +=  callThisPart + " =\n" + "{\n"
      # If the part has a .bestName property set, we'll use it to generate
      # both the .instrumentName and .shortInstrumentName for LilyPond.
      instr_name = s.getInstrument().partName
      if instr_name is not None and len(instr_name) > 0:
         post += '\t%% ' + instr_name + '\n'
         post += '\t\set Staff.instrumentName = \markup{ "' + \
            instr_name + '" }\n'
         if len(instr_name) > 3:
            post += '\t\set Staff.shortInstrumentName = \markup{ "' + \
               instr_name[:3] + '." }\n'
         else:
            post += '\t\set Staff.shortInstrumentName = \markup{ "' + \
               instr_name + '" }\n'
      elif hasattr( s, 'lily_analysis_voice' ) and True == s.lily_analysis_voice:
         the_settings._analysis_notation_parts.append( callThisPart )
         post += '\t%% vis annotated analysis\n'
         post += process_analysis_voice( s )
      #----

      # If it's an analysis-annotation part, we'll handle this differently.
      if hasattr( s, 'lily_analysis_voice' ) and True == s.lily_analysis_voice:
         pass
      # Otherwise, it's hopefully just a regular, everyday Part.
      else:
         # What's in the Part?
         for thing in s:
            # Probably measures.
            if isinstance( thing, stream.Measure ):
               post += process_measure( thing )
            elif isinstance( thing, instrument.Instrument ):
               # We can safely ignore this (for now?) because we already dealt
               # with the part name earlier.
               pass
            # **kern importer garbage... well, it's only garbage to us
            elif isinstance( thing, humdrum.spineParser.MiscTandem ):
               # http://mit.edu/music21/doc/html/moduleHumdrumSpineParser.html
               # Is there really nothing we can use this for? Seems like these
               # exist only to help music21 developers.
               pass
            else:
               raise UnidentifiedObjectError( 'Unknown object in Stream while processing Part: ' + str(thing) )
      # finally, to close the part
      post += "}\n"
   # Header (Metadata) ------------------------------------
   elif isinstance( s, metadata.Metadata ):
      post += "\header {\n"

      if s.composer is not None:
         post += '\tcomposer = \markup{ "' + s.composer.name + '" }\n'
      if s.composers is not None: # I don't really know what to do with non-composer contributors
         pass
      if 'None' != s.date:
         post += '\tdate = "' + str(s.date) + '"\n'
      if s.movementName is not None:
         post += '\tsubtitle = \markup{ "'
         if None != s.movementNumber:
            post += str(s.movementNumber) + ': '
         post += s.movementName + '" }\n'
      if s.opusNumber is not None:
         post += '\topus = "' + str(s.opusNumber) + '"\n'
      if s.title is not None:
         post += '\ttitle = \markup{ \"' + s.title
         if s.alternativeTitle is not None:
            post += '(\\"' + s.alternativeTitle + '\\")'
         post += '" }\n'

      # Extra Formatting Options
      # Tagline
      if the_settings.get_property( 'tagline' ) is None:
         post += '\ttagline = ""\n'
      elif the_settings.get_property( 'tagline' ) == '':
         pass
      else:
         post += '\ttagline = "' + the_settings.get_property( 'tagline' ) + '"\n'

      # close the \header{} block
      post += "}\n"
   # StaffGroup -------------------------------------------
   elif isinstance( s, layout.StaffGroup ):
      # Ignore this undocumented non-feature!
      pass
   # **kern importer garbage... well, it's only garbage to us
   elif isinstance( s, humdrum.spineParser.MiscTandem ):
      # http://mit.edu/music21/doc/html/moduleHumdrumSpineParser.html
      # Is there really nothing we can use this for? Seems like these
      # exist only to help music21 developers.
      pass
   # Something else...
   else:
      raise UnidentifiedObjectError( 'Unknown object in Stream: ' + str(s) )

   return post
# End process_stream() --------------------------------------------------------



#------------------------------------------------------------------------------
class LilyPond_Settings:
   '''
   Holds the settings relevant to output formatting of a LilyPond file.

   List of Settings:
   - bar_numbers : print bar numbers on 'every' bar, the start of every 'system'
      or 'never'
   - tagline : either 'default' ("Music engraving my LilyPond...") or a str
      that is what you want the tagline to be.
   - indent : either 'default' or a str that is the indentation you want (like
      "0\cm" for example)
   - print_instrument_names : True or False whether to print instrument names
   - lilypond_version : a str that contains the LilyPond version (default is
      auto-detection of whatever's installed)
   - lilypond_path : a str that is the full path to the LilyPond executable
   '''
   def __init__( self ):
      # Hold a list of the part names in this Score
      self._partsInThisScore = []
      # Hold a list of the parts that should be written with the VisAnnotation context.
      self._analysis_notation_parts = []
      # Hold the other settings for this Score
      self._secret_settings = {}
      # Establish default values for settings in this Score
      self._secret_settings['bar_numbers'] = 'system' # TODO: implement this
      self._secret_settings['tagline'] = ''
         # empty string means "default tagline"
         # None means "no tagline"
      self._secret_settings['indent'] = None
      self._secret_settings['print_instrument_names'] = True # TODO: implement this
      self._secret_settings['paper_size'] = 'letter'
      # Deal with the LilyPond path and version
      res = detect_lilypond()
      self._secret_settings['lilypond_path'] = res[0]
      self._secret_settings['lilypond_version'] = res[1]
      self._secret_settings['lilypond_version_numbers'] = \
         make_lily_version_numbers( res[1] )


   def set_property( self, setting_name, setting_value=None ):
      '''
      Modify the value of a setting. There are two forms:

      >>> from output_LilyPond import *
      >>> the_settings = LilyPond_Settings()
      >>> the_settings.set_property( 'indent', '4\mm' )
      >>> the_settings.get_property( 'indent' )
      '4\mm'
      '''
      self._secret_settings[setting_name] = setting_value

   def get_property( self, setting_name ):
      return self._secret_settings[setting_name]

# End Class LilyPond_Settings() -----------------------------------------------



#------------------------------------------------------------------------------
def output_the_file( contents, filename='test_output/lily_output' ):
   # TODO: exception handling
   dir = os.path.dirname(filename)
   if not os.path.exists(dir):
      os.makedirs(dir)

   # Is there already an extension?
   if 3 < len(filename) and '.ly' == filename[-3:]:
      extension = ''
   else:
      extension = '.ly'

   return file_outputter( contents, filename, extension )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def run_lilypond( filename, the_settings ):
   '''
   Arguments should be a str that is the file name followed by a
   LilyPond_Settings object.
   '''
   proc = Popen( [the_settings.get_property('lilypond_path'), '--pdf', '-o', filename, filename], stdout=PIPE, stderr=PIPE )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def process_score( the_score, the_settings=None, filename='test_output/lily_output' ):
   '''
   Use this method to output an entire Score object. The second argument is
   an optional LilyPond_Settings object. The third argument is an optional
   filename.
   '''

   if the_settings is None:
      the_settings = LilyPond_Settings()

   score_to_write = process_stream( the_score, the_settings )
   output_result = output_the_file( score_to_write, filename )
   if output_result[1] is not None:
      # There was some sort of error while outputting the file
      raise IOError( 'Could not output file ' + output_result[1] )
   else:
      run_lilypond( output_result[0], the_settings )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def detect_lilypond():
   '''
   Determine the path to LilyPond and its version.

   Returns a 2-tuple with two str objects:
   - the full path of the LilyPond executable
   - the version reported by that executable
   '''
   proc = Popen( ['which', 'lilypond'], stdout=PIPE )
   lily_path = proc.stdout.read()[:-1] # slice gets rid of terminating newline
   proc = Popen( [lily_path, '--version'], stdout=PIPE )
   lv = proc.stdout.read()
   lily_verzh = lv[lv.find('LilyPond')+9:lv.find('\n')]

   return ( lily_path, lily_verzh )
#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
def make_lily_version_numbers( version_str ):
   '''
   Take a str with three integers separated by the '.' character and returns
   a 3-tuplet with the integers.
   '''
   major = int(version_str[:version_str.find('.')])
   version_str = version_str[version_str.find('.')+1:]
   minor = int(version_str[:version_str.find('.')])
   version_str = version_str[version_str.find('.')+1:]
   revision = int(version_str)

   return ( major, minor, revision )
#------------------------------------------------------------------------------



if __name__ == '__main__':
   print( "Sorry, but you cannot run output_LilyPond.py by itself!" )


# TODO: Testing
# - on a Measure, the .lily_invisible property set to True means that the Staff
#   should be have no lines for that Measure (as in \stopStaff) and that all
#   the Note or Rest objects inside should be made into spacing objects ("s")
#   --> this is in the process_measure() method, and there are lots of things
#       that need to be confirmed as appearing invisible
# - whether the "indent" thing from settings is processed
# - make_lily_triangle() in analytic_engine.py
# - providing a filename to process_score() actually outputs there
# - detect_lilypond() : when it works, and when it doesn't
# - whether the thing that calls LilyPond actually uses the auto-detected path
# - update existing tests for whatever stuff I've modified since they worked



















