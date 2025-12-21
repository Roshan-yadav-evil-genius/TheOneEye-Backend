import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich import print
from Node.Core.Node.Core import NodeConfig
from Node.Nodes.Playwright.Freelancer.Bidder import Bidder
from Node.Core.Form.Core.FormSerializer import FormSerializer  # Add this import

if __name__ == "__main__":
    my_node = Bidder(NodeConfig(id="1", type="playwright-freelance-bidder"))
    form =my_node.form()

    print(FormSerializer(form).to_json(),end="-"*20)

    form.update_field('country', 'india')  # Populates states
    print(FormSerializer(form).to_json(),end="-"*20)

    form.update_field('state', 'maharashtra')  # Populates languages
    print(FormSerializer(form).to_json(),end="-"*20)

    form.update_field('language', 'marathi1')  # Populates languages
    print(FormSerializer(form).to_json(),end="-"*20)

    print(form.is_valid())