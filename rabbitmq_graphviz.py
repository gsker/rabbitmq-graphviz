#! /usr/bin/python 


import argparse
import json
import sys

def escape_id(id_str):
    return id_str.replace('-', '').replace('.', '_')

def build_definitions(definitions, vhost, render_producers, render_consumers):

    def is_same_vhost(entity_dict):
        return entity_dict['vhost'] == vhost

    # If there's a queue but no binding, add a default binding 
    #       (to the "" exchange with the queue name as the routing key)
    # That's the normal way a message would get into that queue.
    for queue in definitions['queues']:
        if not [i for i in  definitions['bindings'] if i['destination'] == queue['name'] ]:
            definitions['bindings'].append({'vhost': queue['vhost'], 'destination': queue['name'],
                'routing_key': queue['name'], 'source': 'NULL', 
                'arguments': {}, 'destination_type': 'queue'} 
            )

    # if there is now a binding but no exchange in that vhost that matches, create the exchange
    for binding in definitions['bindings']:
        if not [ e for e in definitions['exchanges']
                    if e['name'] == binding['source'] and e['vhost'] == binding['vhost'] ]:
            definitions['exchanges'].append({'name':binding['source'], 'durable' : True,
                'vhost':binding['vhost'],'internal':True, 'arguments':{},
                'type':'direct','auto_delete':False}
            )

    return ''.join([
        'digraph {\n',
        '  bgcolor=transparent;\n',
        '  truecolor=true;\n',
        '  rankdir=LR;\n',
        '  node [style="filled"];\n\n',
        ''.join([build_queue(q, render_consumers) for q in filter(is_same_vhost, definitions['queues'])]),
        ''.join([build_exchange(x, render_producers) for x in filter(is_same_vhost, definitions['exchanges'])]),
        ''.join([build_binding(b) for b in filter(is_same_vhost, definitions['bindings'])]),
        '}'])

def build_queue(queue, render_consumers):
    q_name = queue['name']
    q_id = escape_id(q_name)
    
    lines = [
        '  subgraph cluster_Q_%s {\n' % q_id,
        '    label="%s";\n' % q_name,
        '    color=transparent;\n',
        '    "Q_%s" [label="{||||}", fillcolor="red", shape="record"];\n' % q_id,
        '  }\n\n']

    if render_consumers:
        lines.append('  "C_%s" [label="C", fillcolor="#33ccff"];' % q_id)
        lines.append('  "Q_%(name)s" -> "C_%(name)s"' % { 'name': q_id})

    return ''.join(lines)

def build_exchange(exchange, render_producers):
    x_name = exchange['name']
    x_id = escape_id(x_name)
                
    lines = [
        '  subgraph cluster_X_%s {\n' % x_id,
        '    label="%s\\ntype=%s";\n' % (x_name, exchange['type']),
        '    color=transparent;\n',
        '    "X_%s" [label="X", fillcolor="#3333CC", shape="ellipse"];\n' % x_id,
        '  }\n\n']

    if render_producers:
        lines.append('  "P_%s" [label="P", style="filled", fillcolor="#00ffff"];' % x_id)
        lines.append('  "P_%(name)s" -> "X_%(name)s";' % { 'name': x_id })

    return ''.join(lines)

def build_binding(binding):
    if binding['destination_type'] == 'exchange':
        return '  X_%s -> X_%s [label="%s"];\n' % (escape_id(binding['source']), escape_id(binding['destination']), binding['routing_key'])
    else:
        return '  X_%s -> Q_%s [label="%s"];\n' % (escape_id(binding['source']), escape_id(binding['destination']), binding['routing_key'])

def parse_args(): 
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--definitions', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
                        help='Definitions file')    
    parser.add_argument('-o', '--outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout,
                        help='Output file')
    parser.add_argument('-p', '--producers', action='store_true', help='Render producers')
    parser.add_argument('-c', '--consumers', action='store_true', help='Render consumers')    
    parser.add_argument('-x', '--vhost', nargs='?', default='/', help='Restrict to this vhost')  
    return parser.parse_args()    

if __name__ == '__main__':
    args = parse_args()

    definitions = json.load(args.definitions)
    args.definitions.close()

    args.outfile.write(build_definitions(definitions, args.vhost, args.producers, args.consumers))
    args.outfile.close()
