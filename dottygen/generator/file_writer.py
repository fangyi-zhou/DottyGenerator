from pathlib import Path
import shutil, os

basic_template_path =  os.path.abspath(os.path.join('dottygen','generator', "templates", "basic.scala"))

class FileWriter:

    def write_to_basic_template(self, output_file, case_classes, effpi_types, functions):
         shutil.copyfile(basic_template_path,output_file)
         with open(output_file) as f:
             newText = f.read().replace('CASE_CLASSES', case_classes).replace("EFFPI_TYPES", effpi_types).replace("FUNCTIONS", functions)

         with open(output_file, "w") as f:
             f.write(newText)


    def append_to_file(self, output_file, output):
        f = Path(output_file)
        with f.open('a') as fp:
            fp.write(output)

class RecurseTypeGenerator:

    def __init__(self):
        self._recurse_file = f"RecurseExtend.scala"
        self._recurse_template = os.path.abspath(os.path.join("dottygen", "generator", "templates", self._recurse_file))
        self._recurse_output = os.path.abspath(os.path.join("effpi", "src", "main","scala", self._recurse_file))
        self._file_writer = FileWriter()

    def setup(self):
       if os.path.exists(self._recurse_output):
            os.remove(self._recurse_output)

       shutil.copyfile(self._recurse_template, self._recurse_output)

    def add_recursion(self, state_id, role):
        new_recursion = f'sealed abstract class Rec{role}{state_id}[A]() extends RecVar[A]("{role}{state_id}")\ncase object Rec{role}{state_id} extends Rec{role}{state_id}[Unit]\n\n'
        self._file_writer.append_to_file(self._recurse_output, new_recursion)

