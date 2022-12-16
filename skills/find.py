import requests
import PyPDF2 as Pdf

from opsdroid.skill import Skill
from opsdroid.matchers import match_always

import nio
import json
import string

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


        for event in state.events:
            url = self.search_content(event, 'url')
            # type check for pdfs
            if url is not None:
                content_type = self.search_content(event, 'mimetype')
                if content_type == 'video/mp4':
                    url = None
                break

        if url is not None:
            url = url[17:]

            self.__spaces[room] = url

            try:
                names = self.parse_pdf(url)
            except Exception:
                names = None

            names = self.alphabetize(names)
            content = []
            for a in string.ascii_lowercase:
                if len(names[a]) > 0:
                    content.append(names[a])

            await self.create_annotation(content, room)

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
        connector = self.opsdroid.get_connector('matrix').connection
        state = await connector.room_get_state(room_id)

        room = await connector.room_create(visibility=nio.RoomVisibility.public, name='List of famous philosophers', alias='',
                                           federate=False)

        await connector.room_put_state(room_id, content={
                    'com.open-tower.msc3574.markup.location': {
                        'com.open-tower.populus.markup.pdf.highlight': {
                            'activityStatus': 'open',
                            'creator': f'{connector.user_id}',
                            'rootContent': {
                                'body': f'Notable Words',
                                'format': 'org.matrix.custom.html',
                                'formatted_body': f'<p>Notable Words</p>\n',
                                'msgtype': 'm.text'
                            },
                            'rootEventId': '$JK7siG-cGhL3hCnk8HTPfxoI3nEutp5SwdfwLCzzq7U'
                        }
                    },
                    'via': ['matrix.org']
                }, event_type='m.space.child', state_key=room.room_id
            )

        for group in content:
            await self.message(connector, room, group)

    async def message(self, connector, room, content):
        comment = ""
        html = ''
        for item in content:
            comment += f'{item}\n\n'
            html += f'<p><a href=\"{self.__search_terms[item]}\">{item}</a></p>\n'

        message_content = {
            "body": f'{comment}',
            "format": "org.matrix.custom.html",
            "formatted_body": f'{html}',
            "msgtype": "m.text",
            "org.matrix.msc1767.message": [
                {
                    "body": f'{comment}',
                    "mimetype": "text/plain"
                },
                {
                    "body": f'{html}',
                    "mimetype": "text/html"
                }
            ]
        }

        response = await connector.room_send(room_id=room.room_id, message_type='m.room.message',
                                             content=message_content)

    def search_content(self, content: dict, search_term: str):
        """Search A Matrix State Event."""
        for item in content:
            if item == search_term:
                return content[item]
            elif isinstance(content[item], dict):
                found = self.search_content(content[item], search_term)
                if found is not None:
                    return found

    def alphabetize(self, list: list, last_name: bool = True):
        alpha_dict = dict.fromkeys(string.ascii_lowercase, [])

        if last_name:
            for i in range(len(list)):
                try:
                    alpha = list[i].split(' ')
                    alpha = alpha[-1][0]
                    alpha = alpha.lower()

                    alpha_dict[alpha] = alpha_dict[alpha] + [list[i]]
                except Exception as e:
                    print('EXCEPTION: ', e, 'CASE: ', list[i], 'ALPHA: ', alpha)
        else:
            for item in list:
                try:
                    letter = item[0].lower()
                    alpha_dict[letter].append(item)
                except Exception as e:
                    print('EXCEPTION: ', e, 'CASE: ', item)

        return alpha_dict


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
            item = item.replace(' ', '')
            if item in pdf_str:
                term_list.append(term)

        return term_list


if __name__ == '__main__':
    pdf = PdfParse('download.pdf')