import requests
import PyPDF2 as Pdf

from opsdroid.skill import Skill
from opsdroid.matchers import match_always

import nio
import json

class PhiloFinder(Skill):

    def __init__(self, opsdroid, config):
        super(PhiloFinder, self).__init__(opsdroid, config)
        
        self.opsdroid = opsdroid

        self.__spaces = {}

        setup = config['setup']
        with open(setup) as s:
            self.__search_terms = json.load(s)

    @match_always()
    async def get_pdf(self, event):
        connector = self.opsdroid.get_connector('matrix').connection
        rooms = await connector.joined_rooms()
        rooms = rooms.rooms

        if len(self.__spaces) == 0:
            for room in rooms:
                await self.search_room(room, connector)
        elif len(self.__spaces) < len(rooms):
            for room in rooms:
                if room not in self.__spaces.keys():
                    await self.search_room(room, connector)

    async def search_room(self, room, connector):
        """Search for matrix rooms with downloadable content"""
        state = await connector.room_get_state(room)

        # TO DO: type check for pdfs

        for event in state.events:
            url = self.search_content(event, 'url')
            if url is not None:
                break

        if url is not None:
            url = url[17:]

            self.__spaces[room] = url

            try:
                names = self.parse_pdf(url)
            except Exception:
                names = None

            if names is not None:
                await self.create_annotation(names, room)

    def download_pdf(self, url):
        """Use a Matrix URI to download the pages pdf"""
        response = requests.get(f'https://matrix.org/_matrix/media/v3/download/matrix.org/{url}/test.pdf')
        # Write content in pdf file
        pdf = open("download.pdf", 'wb')
        pdf.write(response.content)

        return True

    def parse_pdf(self, url):
        """Use PdfParse to search the pdf"""
        self.download_pdf(url)
        pdf = PdfParse('download.pdf')

        return pdf.parse(self.__search_terms.keys())

    async def create_annotation(self, content: list, room_id: str):
        """Create a Populus annotation"""
        comment = "Philosophers of Note:\n"
        for item in content:
            comment += f'{item}: {self.__search_terms[item]}\n'

        connector = self.opsdroid.get_connector('matrix').connection
        await connector.room_get_state(room_id)

        room = await connector.room_create(visibility=nio.RoomVisibility.public, name='List of famous philosophers', alias='',
                                           federate=False)

        await connector.room_put_state(room_id, content={
                    'com.open-tower.msc3574.markup.location': {
                        'com.open-tower.populus.markup.pdf.highlight': {
                            'activityStatus': 'open',
                            'creator': f'{connector.user_id}',
                            'rootContent': {
                                'body': f'{comment}', # TO DO: formating in comment
                                'format': 'org.matrix.custom.html',
                                'formatted_body': f'<p>{comment}</p>\n',
                                'msgtype': 'm.text'
                            },
                            'rootEventId': '$JK7siG-cGhL3hCnk8HTPfxoI3nEutp5SwdfwLCzzq7U'
                        }
                    },
                    'via': ['matrix.org']
                }, event_type='m.space.child', state_key=room.room_id
            )

    def search_content(self, content: dict, search_term: str):
        """Search A Matrix State Event."""
        for item in content:
            if item == search_term:
                return content[item]
            elif isinstance(content[item], dict):
                found = self.search_content(content[item], search_term)
                if found is not None:
                    return found


class PdfParse:
    """Parse PDF

        Takes a pdf and looks the search terms you give it
    """
    def __init__(self, pdf_str: str):
        self.__pdf = Pdf.PdfReader(pdf_str)

        # TO DO: alternate parse methods if this one doesn't work

    def parse(self, terms):

        pdf_str = str()

        for i in range(len(self.__pdf.pages)):
            pdf_page = self.__pdf.pages[i].extract_text()

            for char in pdf_page:
                if char != '\n' and char != ' ':
                    char = char.lower()
                    pdf_str += char

        term_list = list()
        for term in terms:
            item = term.lower()
            if item in pdf_str:
                term_list.append(term)

        return term_list
